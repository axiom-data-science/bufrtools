#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Module for basic and general parsing functions."""
from pathlib import Path

import cftime
import pandas as pd
from pocean.dsg import *  # noqa Import required for CFDataset
from pocean.cf import CFDataset


def parse_ref(fxy) -> tuple:
    """Returns a tuple of the FXXYYYY string parsed out into integers."""
    f = int(fxy[0])
    x = int(fxy[1:3])
    y = int(fxy[3:6])
    return f, x, y


def load_csv(ipt: Path) -> pd.DataFrame:
    df = pd.read_csv(ipt)
    df['time'] = pd.to_datetime(df.time)
    return (
        df,
        {}
    )


def load_parquet(ipt: Path) -> pd.DataFrame:
    return (
        pd.read_parquet(ipt),
        {}
    )


def load_netcdf(ipt: Path) -> pd.DataFrame:
    ds = CFDataset.load(str(ipt))
    axes = dict(
        t='time',
        z='z',
        x='lon',
        y='lat',
        profile='profile',
        trajectory='trajectory'
    )

    meta = ds.meta()['attributes']
    valid_meta = {
        'uuid': meta.get('uuid')['data'],
        'ptt': meta.get('ptt', '')['data']
    }
    df = ds.to_dataframe(axes=axes, clean_cols=False, clean_rows=False)

    try:
        df.time.astype(int)
    except TypeError:
        if isinstance(df.time.iloc[0], cftime.datetime):
            df['time'] = df.time.apply(lambda x: x._to_real_datetime())
        else:
            raise ValueError("Could not find a pandas compatible 'time' column")

    return (
        df,
        valid_meta
    )


def parse_input_to_dataframe(ipt: Path) -> pd.DataFrame:
    # Shortcut to avoid needing a file at all
    if isinstance(ipt, pd.DataFrame):
        return (ipt, {})
    else:
        # Try to load as a pandas dataset file
        loaders = [
            load_csv,
            load_parquet,
            load_netcdf
        ]
        for load_func in loaders:
            try:
                return load_func(ipt)
            except BaseException:
                pass
        raise ValueError(f"Could not load {ipt} as a dataset")
