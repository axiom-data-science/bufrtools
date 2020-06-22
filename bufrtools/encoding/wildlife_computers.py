#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Encoding support for wildlife computers netCDF."""


import numpy as np
import pandas as pd
import cftime
import sys
import io
from pathlib import Path
import pocean  # noqa Import required for CFDataset
import pocean.dsg  # noqa Import required for CFDataset
from pocean.cf import CFDataset
from datetime import datetime
from bufrtools.tables import get_sequence_description
from bufrtools import encode_animal_tag as encoder
from typing import List
from argparse import ArgumentParser, Namespace
from bufrtools.util.gis import haversine_distance, azimuth


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
        'master_table_version': 33,  # Future version
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
        'descriptors': ['315013'],
    }
    return section3


def drift(ncd: CFDataset) -> np.ndarray:
    """Returns the speed/drift values for the dataset.

    This function calculates drift by computer the haversine equation of the coordinates and
    dividing them by the time difference between each point. Values for trajectory segments that
    travel no distance over no time will have a drift of zero. The last element of the returned
    array will be 0, as it can not be effectively calculated.
    """
    t = ncd.variables['time'][:]
    dt = np.diff(t)
    assert 'seconds' in ncd.variables['time'].units
    x = ncd.variables['lon'][:] * np.pi / 180
    y = ncd.variables['lat'][:] * np.pi / 180
    ds = haversine_distance(x, y)
    ds_dt = np.zeros_like(t)
    for i in range(ds.shape[0]):
        if np.abs(ds[i]) < 0.0001 and np.abs(dt[i]) < 0.0001:
            ds_dt[i] = 0
        else:
            ds_dt[i] = ds[i] / dt[i]
    return ds_dt


def get_trajectory_sequences(ncd, df) -> List[dict]:
    """Returns a sequence of records for the trajectory part of the BUFR message."""
    dates = cftime.num2date(ncd.variables['time'][:], units=ncd.variables['time'].units)
    x = ncd.variables['lon'][:] * np.pi / 180
    y = ncd.variables['lat'][:] * np.pi / 180
    theta = azimuth(x, y) * 180 / np.pi
    theta = (theta + 360) % 360
    speed = drift(ncd)
    trajectory = pd.DataFrame({
        'profile': ncd.variables['profile'][:-1],
        'time': dates[:-1],
        'latitude': ncd.variables['lat'][:-1],
        'longitude': ncd.variables['lon'][:-1],
        'direction': theta[:-1],
        'speed': speed[:-1],
    })
    trajectory = trajectory[trajectory.speed > 0]
    trajectory['z'] = df.groupby('profile')['z'].min()
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
    trajectory_seq = get_sequence_description('315013').iloc[16:35]
    for i, row in trajectory.iterrows():
        for seq in process_trajectory(trajectory_seq.copy(), row):
            sequence.append(seq)
    return sequence


def process_trajectory(trajectory_seq: pd.DataFrame, row) -> List[dict]:
    """Returns the sequence for the given row of the trajectory data frame."""
    trajectory_seq['value'] = [
        26,                         # Last known position
        np.nan,                     # Sequence
        row.time.year,
        row.time.month,
        row.time.day,
        np.nan,                     # Sequence
        row.time.hour,
        row.time.minute,
        np.nan,                     # Lat/Lon Sequence,
        row.latitude,
        row.longitude,
        row.direction,
        row.speed,
        0,                          # Fixed to good
        0,                          # Fixed to good
        1,                          # 500 m <= Radius <= 1500 m
        row.z if row.z >= 0 else 0,
        row.temperature,
        31,                         # Missing Value
    ]
    return trajectory_seq.to_dict(orient='records')


def get_profile_sequence(ncd, df) -> List[dict]:
    """Returns the sequences for the profiles."""
    parent_seq = get_sequence_description('315013')
    profile_description_seq = parent_seq.iloc[37:50]
    profile_data_seq = parent_seq.iloc[53:65]
    sequence = []
    sequence.append({
        'fxy': '031001',
        'text': 'Delayed descriptor replication factor (Numeric)',
        'type': 'numeric',
        'scale': 0,
        'offset': 0,
        'bit_len': 8,
        'value': ncd.variables['profile'].shape[0],
    })
    for profile_id in ncd.variables['profile'][:]:
        profile = df[df['profile'] == profile_id]
        profile_seq = process_profile_description(profile_description_seq.copy(), profile)
        sequence.extend(profile_seq)
        data_seq = process_profile_data(profile_data_seq.copy(), profile)
        sequence.extend(data_seq)
    return sequence


def process_profile_description(profile_seq: pd.DataFrame, profile: pd.DataFrame) -> List[dict]:
    """Returns the sequence for the profile description part."""
    date = profile.iloc[0]['t']
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    minute = date.minute
    latitude = profile.iloc[0]['y']
    longitude = profile.iloc[0]['x']
    profile_id = str(profile.iloc[0]['profile'])
    seq_no = profile.iloc[0]['profile']
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
        latitude,
        longitude,
        profile_id,
        seq_no,
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
        seq['value'] = [
            row.z if row.z > 0 else 0,  # Depth below sea water
            13,                         # Depth at a level
            0,                          # Unqualified
            0,                          # Pressure is not available
            10,                         # Pressure at a level
            0,                          # Unqualified
            row.temperature + 273.15,   # Temperature in K
            11,                         # Temperature at a depth
            0,                          # Unqualified
            0,                          # Salinity
            12,                         # Salinity at a depth
            0,                          # Unqualified
        ]
        sequence.extend(seq.to_dict(orient='records'))
    return sequence


def get_section4(ncd) -> List[dict]:
    """Returns the section4 data."""
    records = []
    wigos_sequence = get_sequence_description('301150')

    wigos_identifier_series = 0  # Placeholder
    wigos_issuer = 2202
    wigos_issue_number = 0  # Placeholder
    wigos_local_identifier = 'to be determined'
    wigos_sequence['value'] = [
        np.nan,
        wigos_identifier_series,
        wigos_issuer,
        wigos_issue_number,
        wigos_local_identifier,
    ]
    records.extend(wigos_sequence.to_dict(orient='records'))

    platform_id_sequence = get_sequence_description('315013')[6:14]
    platform_id_sequence['value'] = [
        123,            # WMO ID
        np.nan,         # operator
        ncd.uuid[:32],  # Long station or site name
        np.nan,         # operator
        11,             # Marine animal
        995,            # Attached to marine animal
        ncd.ptt[:12],
        1,              # Argos
    ]
    records.extend(platform_id_sequence.to_dict(orient='records'))
    # WC profiles don't have enough data to fill in the trajectory portion of the BUFR, so we'll
    df = ncd.to_dataframe()
    records.extend(get_trajectory_sequences(ncd, df))
    records.extend(get_profile_sequence(ncd, df))
    return records


def encode(profile_dataset: Path, output: Path):
    """Encodes the netCDF `profile_dataset` as BUFR and writes it to `output`."""
    ncd = CFDataset.load(str(profile_dataset))
    context = {}
    context['buf'] = buf = io.BytesIO()
    encoder.encode_section0({}, context)
    section1 = get_section1()
    encoder.encode_section1({'section1': section1}, context)
    section3 = get_section3()
    encoder.encode_section3({'section3': section3}, context)
    section4 = get_section4(ncd)
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
    parser.add_argument('profile_dataset', type=Path, help='ATN Wildlife Comptuers profile netCDF')

    args = parser.parse_args(argv)
    return args


def main():
    """Encode a wildlife computers profile."""
    args = parse_args(sys.argv[1:])

    assert args.profile_dataset.exists()
    encode(args.profile_dataset, args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
