#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Encoding support for wildlife computers netCDF."""


import io
import sys
from typing import List
from pathlib import Path
from argparse import Namespace, ArgumentParser
from datetime import datetime

import numpy as np
import pandas as pd

from bufrtools.tables import get_sequence_description
from bufrtools.encoding import bufr as encoder
from bufrtools.util.gis import azimuth, haversine_distance
from bufrtools.util.parse import parse_input_to_dataframe


def get_section1() -> dict:
    """Returns the section1 part of the message to be encoded."""
    now = datetime.utcnow()
    section1 = {
        'originating_centre': 177,
        'sub_centre': 0,
        'data_category': 31,         # oceanographic data
        'sub_category': 4,           # subsurface float (profile)
        'local_category': 0,         # Ideally something specifies this as a marine mammal
                                     # animal tag
        'master_table_version': 39,
        'local_table_version': 255,  # Unknown
        'year': now.year,
        'month': now.month,
        'day': now.day,
        'hour': now.hour,
        'minute': now.minute,
        'second': now.second,
        'seq_no': 0,                 # Original message
    }
    return section1


def get_section3() -> dict:
    """Returns the section3 part of the message to be encoded."""
    section3 = {
        'number_of_subsets': 1,
        'observed_flag': True,
        'compressed_flag': False,
        'descriptors': ['315023'],
    }
    return section3


def drift(df: pd.DataFrame) -> np.ndarray:
    """Returns the speed/drift values for the dataset.

    This function calculates drift by computer the haversine equation of the coordinates and
    dividing them by the time difference between each point. Values for trajectory segments that
    travel no distance over no time will have a drift of zero. The last element of the returned
    array will be 0, as it can not be effectively calculated.
    """
    # Convert to epoch seconds
    t = df.groupby('profile')['time'].first().view('int64') // 1e9
    dt = np.diff(t)

    x = df.groupby('profile')['lon'].first() * np.pi / 180
    y = df.groupby('profile')['lat'].first() * np.pi / 180
    ds = haversine_distance(x.values, y.values)
    ds_dt = np.zeros_like(t)
    for i in range(ds.shape[0]):
        if np.abs(ds[i]) < 0.0001 and np.abs(dt[i]) < 0.0001:
            ds_dt[i] = 0
        else:
            ds_dt[i] = ds[i] / dt[i]
    return ds_dt


def get_trajectory_sequences(df: pd.DataFrame) -> List[dict]:
    """Returns a sequence of records for the trajectory part of the BUFR message."""
    # Pull profile locations out as the first point in each profile
    t = df.groupby('profile')['time'].first()
    x = df.groupby('profile')['lon'].first() * np.pi / 180
    y = df.groupby('profile')['lat'].first() * np.pi / 180

    theta = azimuth(x.values, y.values) * 180 / np.pi
    theta_mask = ~np.isnan(theta)
    theta[theta_mask] = (theta[theta_mask] + 360) % 360
    speed = drift(df)

    trajectory = pd.DataFrame({
        'time': t[:-1],
        'profile': df.groupby('profile')['profile'].first()[:-1],
        'lat': df.groupby('profile')['lat'].first()[:-1],
        'lon': df.groupby('profile')['lon'].first()[:-1],
        'direction': theta[:-1],
        'speed': speed[:-1]
    })

    trajectory = trajectory[trajectory.speed > 0]
    trajectory['z'] = df.groupby('profile')['z'].min()
    # Should we ever have a negative depth?
    #trajectory['z'] = trajectory.z.apply(lambda x: max(0, x))
    # Drop the profile index before merge
    trajectory = trajectory.reset_index(drop=True)
    # Combine back with the full dataset after calculating
    # speed and direction
    trajectory = pd.merge(trajectory, df[['profile', 'z', 'temperature']])
    sequence = []
    sequence.append({
        'fxy': '031001',
        'text': 'Delayed descriptor replication factor (Numeric)',
        'type': 'numeric',
        'scale': 0,
        'offset': 0,
        'bit_len': 8,
        'value': len(trajectory)
    })
    trajectory_seq = get_sequence_description('315023').iloc[18:37]
    for _, row in trajectory.iterrows():
        for seq in process_trajectory(trajectory_seq.copy(), row):
            sequence.append(seq)
    return sequence


def process_trajectory(trajectory_seq: pd.DataFrame, row) -> List[dict]:
    """Returns the sequence for the given row of the trajectory data frame."""

    # Get temperature
    temperature = getattr(row, 'temperature', np.nan)
    temperature += 273.15  # Convert from deg_C to Kelvin

    trajectory_seq['value'] = [
        26,                          # Last known position
        np.nan,                      # Sequence
        row.time.year,
        row.time.month,
        row.time.day,
        np.nan,                      # Sequence
        row.time.hour,
        row.time.minute,
        np.nan,                      # Lat/Lon Sequence,
        row.lat,
        row.lon,
        row.direction,
        row.speed,
        0,                           # Fixed to good
        0,                           # Fixed to good
        1,                           # 500 m <= Radius <= 1500 m
        row.z if row.z >= 0 else 0,
        temperature,                 # Sea / Water Temperature (K)
        31,                          # Missing Value
    ]
    return trajectory_seq.to_dict(orient='records')


def get_profile_sequence(df: pd.DataFrame) -> List[dict]:
    """Returns the sequences for the profiles."""
    parent_seq = get_sequence_description('315023')
    profile_description_seq = parent_seq.iloc[39:52]
    profile_data_seq = parent_seq.iloc[55:67]
    sequence = []
    sequence.append({
        'fxy': '031001',
        'text': 'Delayed descriptor replication factor (Numeric)',
        'type': 'numeric',
        'scale': 0,
        'offset': 0,
        'bit_len': 8,
        'value': len(df.profile.unique()),
    })
    for profile_id in df.profile.unique():
        profile = df[df['profile'] == profile_id]
        profile_seq = process_profile_description(profile_description_seq.copy(), profile)
        sequence.extend(profile_seq)
        data_seq = process_profile_data(profile_data_seq.copy(), profile)
        sequence.extend(data_seq)
    return sequence


def process_profile_description(profile_seq: pd.DataFrame, profile: pd.DataFrame) -> List[dict]:
    """Returns the sequence for the profile description part."""
    first_row = profile.iloc[0]
    date = first_row.time

    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    minute = date.minute
    lat = first_row.lat
    lon = first_row.lon
    profile_id = str(first_row.profile)
    direction = 0 if (profile.z.mean() < 0) else 1
    profile_seq['value'] = [
        np.nan,     # Sequence
        year,
        month,
        day,
        np.nan,     # Sequence
        hour,
        minute,
        np.nan,     # Sequence
        lat,
        lon,
        profile_id,
        np.nan,     # Upcast number
        direction,
    ]
    return profile_seq.to_dict(orient='records')


def process_profile_data(profile_seq: pd.DataFrame, profile: pd.DataFrame) -> List[dict]:
    """Returns the sequence for the profile data 306035 Temperature and Salinity Profile."""
    sequence = []
    sequence.append({
        'fxy': '031002',
        'text': 'Delayed descriptor replication factor (Numeric)',
        'type': 'numeric',
        'scale': 0,
        'offset': 0,
        'bit_len': 16,
        'value': len(profile),
    })
    for i, row in profile.iterrows():
        seq = profile_seq.copy()

        # Get pressure
        pressure = getattr(row, 'pressure', np.nan)
        pressure *= 10000  # Convert from dbar to Pa
        # Get temperature
        temperature = getattr(row, 'temperature', np.nan)
        temperature += 273.15  # Convert from deg_C to Kelvin
        # Get salinity
        salinity = getattr(row, 'salinity', np.nan)

        seq['value'] = [
            row.z if row.z > 0 else 0,  # Depth below sea water
            13,                         # Depth at a level
            0,                          # Unqualified
            pressure,                   # Pressure
            10,                         # Pressure at a level
            0,                          # Unqualified
            temperature,                # Temperature in K
            11,                         # Temperature at a depth
            0,                          # Unqualified
            salinity,                   # Salinity
            12,                         # Salinity at a depth
            0,                          # Unqualified
        ]
        sequence.extend(seq.to_dict(orient='records'))
    return sequence


def get_section4(df: pd.DataFrame, **kwargs) -> List[dict]:
    """Returns the section4 data."""
    records = []

    wigos_issuer = int(kwargs.pop('wigos_issuer', 22000))
    wigos_local_identifier = str(kwargs.pop('wigos_platform_code', ''))
    wigos_identifier_series = 0  # Placeholder
    wigos_issue_number = 0       # Placeholder

    wigos_sequence = get_sequence_description('301150')
    wigos_sequence['value'] = [
        np.nan,                   # Sequence
        wigos_identifier_series,  # 001125,WIGOS identifier series,,,Operational
        wigos_issuer,             # 001126,WIGOS issuer of identifier,,,Operational
        wigos_issue_number,       # 001127,WIGOS issue number,,,Operational
        wigos_local_identifier,   # 001128,WIGOS local identifier (character),,,Operational
    ]
    records.extend(wigos_sequence.to_dict(orient='records'))

    uuid = kwargs.pop('uuid')
    ptt = kwargs.pop('ptt')
    wmo = kwargs.pop('wmo_platform_code', None)
    # If WMO ID is passed in as None, fill it with zero
    if wmo is None:
        wmo = 0

    platform_id_sequence = get_sequence_description('315023')[6:16]
    platform_id_sequence['value'] = [
        np.nan,         # 201129,Change data width,,,Operational  # noqa
        wmo,            # 001087,WMO marine observing platform extended identifier ,WMO number where assigned,,Operational # noqa
        np.nan,         # 201000,Change data width,Cancel,,Operational
        np.nan,         # 208032,Change width of CCITT IA5 ,change width to 32 characters,,Operational # noqa
        uuid[:32],      # 001019,Ship or mobile land station identifier ,"Platform ID, e.g. ct145-933-BAT2-18 (max 32 characters)",,Operational # noqa
        np.nan,         # 208000,Change width of CCITT IA5 ,Cancel change width,,Operational # noqa
        10,             # 003001,Surface station type ,10 (Marine animal),,Operational # noqa
        995,            # 022067,Instrument type for water temperature and/or salinity measurement,set to 995 (attached to marine animal),,Operational # noqa
        ptt[:12],       # 001051,Platform transmitter ID number,e.g. Argos PTT,,Operational # noqa
        1,              # 002148,Data collection and/or location system,,,Operational # noqa
    ]
    records.extend(platform_id_sequence.to_dict(orient='records'))
    # WC profiles don't have enough data to fill in the trajectory portion of the BUFR, so we'll
    records.extend(get_trajectory_sequences(df))
    records.extend(get_profile_sequence(df))
    return records


def encode(profile_dataset: Path, output: Path, **kwargs):
    """Encodes the input `profile_dataset` as BUFR and writes it to `output`."""
    df, meta = parse_input_to_dataframe(profile_dataset)

    # If we were able to extract metadata attributes from the
    # source dataset, use those instead of the passed in values
    if meta:
        kwargs = {**kwargs, **meta}

    context = {}
    context['buf'] = buf = io.BytesIO()
    encoder.encode_section0({}, context)
    section1 = get_section1()
    encoder.encode_section1({'section1': section1}, context)
    section3 = get_section3()
    encoder.encode_section3({'section3': section3}, context)
    section4 = get_section4(df, **kwargs)
    encoder.encode_section4({'section4': section4}, context)
    encoder.encode_section5(context)
    encoder.finalize_bufr(context)

    buf.seek(0)
    output.write_bytes(buf.read())


def parse_args(argv) -> Namespace:
    """Returns the namespace parsed from the command line arguments."""
    parser = ArgumentParser(description=main.__doc__)
    parser.add_argument('-o',
                        '--output',
                        type=Path,
                        default=Path('output.bufr'), help='Output file')
    parser.add_argument('profile_dataset', type=Path, help='ATN Wildlife Computers profile netCDF')
    parser.add_argument('-u',
                        '--uuid',
                        type=str,
                        default=None)
    parser.add_argument('-p',
                        '--ptt',
                        type=str,
                        default=None)

    args = parser.parse_args(argv)
    return args


def main():
    """Encode a wildlife computers profile."""
    args = parse_args(sys.argv[1:])

    assert args.profile_dataset.exists()
    encode(args.profile_dataset, args.output, uuid=args.uuid, ptt=args.ptt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
