#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Package for dealing with BUFR tables."""
import csv
import copy
import codecs

import pkg_resources

import numpy as np
import pandas as pd
from bufrtools.util.parse import parse_ref


def get_code_table(fxy_str: str) -> pd.DataFrame:
    """Returns the code table for the given FXXYYY string."""
    f, x, y = parse_ref(fxy_str)
    filename = f'BUFRCREX_CodeFlag_en_{x:02d}.csv'
    utf8_reader = codecs.getreader('utf-8')
    with pkg_resources.resource_stream('bufrtools.tables', f'data/{filename}') as f:
        reader = csv.DictReader(utf8_reader(f))
        rows = []
        for row in reader:
            if fxy_str != row['FXY']:
                continue
            if '-' in row['CodeFigure']:
                start, end = (int(i) for i in row['CodeFigure'].split('-'))
                for i in range(start, end + 1):
                    enumerated_row = copy.copy(row)
                    enumerated_row['CodeFigure'] = i
                    rows.append(enumerated_row)
            else:
                rows.append(row)
    df = pd.DataFrame(rows)
    df = df.astype({'CodeFigure': np.uint16})
    return df


def get_code_table_figure(fxy_str: str, code_figure: int) -> dict:
    """Returns the code table row for the given FXXYYY string."""
    f, x, y = parse_ref(fxy_str)
    filename = f'BUFRCREX_CodeFlag_en_{x:02d}.csv'
    utf8_reader = codecs.getreader('utf-8')
    with pkg_resources.resource_stream('bufrtools.tables', f'data/{filename}') as f:
        reader = csv.DictReader(utf8_reader(f))
        for row in reader:
            if fxy_str != row['FXY']:
                continue
            if '-' in row['CodeFigure']:
                start, end = (int(i) for i in row['CodeFigure'].split('-'))
                if start <= code_figure and code_figure <= end:
                    return row
            else:
                try:
                    val = int(row['CodeFigure'])
                    if val == code_figure:
                        return row
                except ValueError:
                    pass


def get_summary(fxy_str: str) -> pd.DataFrame:
    """Returns a summary table of the contents of the FXXYYY sequence."""
    f, x, y = parse_ref(fxy_str)
    references = table_d_lookup(f, x, y)
    df = combine_references(references)
    columns = [
        'Parent',
        'FXY',
        'Title',
        'Subtitle',
        'BUFR_DataWidth_Bits',
        'BUFR_Unit',
        'BUFR_Scale',
        'BUFR_ReferenceValue',
    ]
    return df[columns]


def get_sequence_description(fxy_str: str) -> pd.DataFrame:
    """Returns a sequence description used for encoding/decoding."""
    summary = get_summary(fxy_str).copy(deep=True)
    # Get rid of the old index because it references a combination of other tables
    summary.reset_index(drop=True, inplace=True)
    summary.rename(columns={
        'BUFR_Scale': 'scale',
        'BUFR_ReferenceValue': 'offset',
        'FXY': 'fxy',
        'Parent': 'parent',
        'BUFR_DataWidth_Bits': 'bit_len',
    }, inplace=True)
    summary['type'] = np.nan
    summary['text'] = summary['Title']
    for i, row in summary.iterrows():
        f, x, y = parse_ref(row['fxy'])
        typename = ''
        title = f'{row["Title"]} ({row["BUFR_Unit"]})'
        if f == 2:
            typename = 'operator'
        elif row['BUFR_Unit'] == 'CCITT IA5':
            typename = 'string'
        elif row['BUFR_Unit'] == 'Replication':
            typename = 'replication'
        else:
            typename = 'numeric'
        summary.iloc[i, summary.columns.get_loc('type')] = typename
        summary.iloc[i, summary.columns.get_loc('text')] = title
    return summary


def get_table_a() -> pd.DataFrame:
    """Returns the Table A contents."""
    filename = 'BUFR_TableA_en.csv'
    stream = pkg_resources.resource_stream('bufrtools.tables', f'data/{filename}')
    df = pd.read_csv(stream)
    return df


def get_table_d(f, x, y) -> pd.DataFrame:
    """Returns the contents of the Table D for the given FXXYYY string."""
    assert f == 3
    fxy_str = f'{f}{x:02d}{y:03d}'
    filename = f'BUFR_TableD_en_{x:02d}.csv'
    stream = pkg_resources.resource_stream('bufrtools.tables', f'data/{filename}')
    df = pd.read_csv(stream, dtype={'FXY1': str, 'FXY2': str})
    df = df[df['FXY1'] == fxy_str]
    return df


def get_table_b(f, x, y) -> pd.DataFrame:
    """Returns the contents of the Table B for the given FXXYYY string."""
    assert f == 0
    fxy_str = f'{f}{x:02d}{y:03d}'
    filename = f'BUFRCREX_TableB_en_{x:02d}.csv'
    stream = pkg_resources.resource_stream('bufrtools.tables', f'data/{filename}')
    df = pd.read_csv(stream, dtype={'FXY': str})
    df = df[df['FXY'] == fxy_str]
    return df


def table_a_lookup(code_figure: int) -> dict:
    """Returns the data for a given table a code figure."""
    df = get_table_a()
    rec = df.loc[code_figure]
    return rec.to_dict()


def table_d_lookup(f, x, y, parent=None):
    """Returns a data frame for a Table D."""
    df = get_table_d(f, x, y)
    sub_references = []
    fxy_str = f'{f}{x:02d}{y:03d}'
    if parent is None:
        title = df.iloc[0]['Title_en']
        subtitle = ''
        sub_references.append((fxy_str, fxy_str, title, subtitle))
        parent = fxy_str
    for _, row in df.iterrows():
        ref = row['FXY2']
        title = row['ElementName_en']
        subtitle = row['ElementDescription_en']
        ref_f, ref_x, ref_y = parse_ref(ref)
        if ref_f == 0:
            sub_references.append((parent, ref, title, subtitle))
        if ref_f == 2 and ref_x in [1, 8]:
            sub_references.append((parent, ref, title, subtitle))
        if ref_f == 1:
            sub_references.append((parent, ref, title, subtitle))
        if ref_f == 3:
            sub_references.append((parent, ref, title, subtitle))
            sub_refs = table_d_lookup(ref_f, ref_x, ref_y, ref)
            sub_references.extend(sub_refs)
    return sub_references


def combine_references(references) -> pd.DataFrame:
    """Returns a data frame for a generic reference, that will be flattened."""
    frames = []
    for parent, reference, title, subtitle in references:
        f, x, y = parse_ref(reference)
        if f == 2 and x == 8:
            frames.append(pd.DataFrame([{
                'Parent': parent,
                'FXY': f'{f}{x:02d}{y:03d}',
                'ElementName_en': f'Operator Change CCITT IA5 width to {8 * y}',
                'BUFR_DataWidth_Bits': 0,
                'BUFR_Unit': 'Operator',
                'Title': title,
                'Subtitle': subtitle,
            }]))
        elif f == 2 and x == 1 and y == 129:
            frames.append(pd.DataFrame([{
                'Parent': parent,
                'FXY': f'{f}{x:02d}{y:03d}',
                'ElementName_en': 'Change data width',
                'BUFR_DataWidth_Bits': 0,
                'BUFR_Unit': 'Operator',
                'Title': title,
                'Subtitle': subtitle,
            }]))
        elif f == 2 and x == 1 and y == 0:
            frames.append(pd.DataFrame([{
                'Parent': parent,
                'FXY': f'{f}{x:02d}{y:03d}',
                'ElementName_en': 'Cancel change data width',
                'BUFR_DataWidth_Bits': 0,
                'BUFR_Unit': 'Operator',
                'Title': title,
                'Subtitle': subtitle,
            }]))
        elif f == 1:
            if y == 0:
                frames.append(pd.DataFrame([{
                    'Parent': parent,
                    'FXY': f'{f}{x:02d}{y:03d}',
                    'ClassName_en': 'Replication',
                    'ElementName_en': f'Delayed Replication: {x}',
                    'BUFR_DataWidth_Bits': 0,
                    'BUFR_Unit': 'Replication',
                    'Title': title,
                    'Subtitle': subtitle,
                }]))
            else:
                frames.append(pd.DataFrame([{
                    'Parent': parent,
                    'FXY': f'{f}{x:02d}{y:03d}',
                    'ClassName_en': 'Replication',
                    'ElementName_en': f'Replication {x}',
                    'BUFR_DataWidth_Bits': 0,
                    'BUFR_Unit': 'Replication',
                    'Title': title,
                    'Subtitle': subtitle,
                }]))
        elif f == 3:
            df = get_table_d(f, x, y)
            name = df.iloc[0]['Title_en']
            frames.append(pd.DataFrame([{
                'Parent': parent,
                'FXY': f'{f}{x:02d}{y:03d}',
                'ClassName_en': 'sequence',
                'ElementName_en': f'{name}',
                'BUFR_DataWidth_Bits': 0,
                'BUFR_Unit': 'Sequence',
                'Title': title,
                'Subtitle': subtitle,
            }]))
        else:
            df = get_table_b(f, x, y)
            df['Parent'] = parent
            df['Title'] = title
            df['Subtitle'] = subtitle
            frames.append(df)
    return pd.concat(frames, sort=True)
