#!/usr/bin/env pytest
#-*- coding: utf-8 -*-
"""Unit tests for wildlife computers."""
import os
import tempfile
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch

import pytest

import bufrtools
from bufrtools import decoding
from bufrtools.encoding import wildlife_computers


def get_example_path(example_name: str) -> Path:
    """Returns the path to an eample."""
    root = Path(bufrtools.__file__).parent.parent
    examples = Path(root, 'examples')
    filepath = Path(examples, example_name)
    return filepath


@pytest.fixture
def tempfile_fixture():
    """Fixture for temporary files to be used as output."""
    fd, name = tempfile.mkstemp(suffix='.bufr', prefix='animaltag')
    os.close(fd)
    yield name
    os.unlink(name)


@patch('bufrtools.encoding.wildlife_computers.parse_args')
def test_wildlife_computers_encoding_from_netcdf(parse_args, tempfile_fixture):
    """Tests for encoding the wildlife computers profile data."""
    args = Namespace(
        output=Path(tempfile_fixture),
        profile_dataset=get_example_path('profile.nc'),
        uuid=None,
        ptt=None
    )
    parse_args.return_value = args
    wildlife_computers.main()

    with open(tempfile_fixture, 'rb') as f:
        file_id = f.read(4)
        assert file_id == b'BUFR'
        total_size = decoding.parse_unsigned_int(f.read(3), 24)
        assert total_size == 29218
        # f.seek(112)
        # # Verify that there are 88 points in the trajectory
        # delayed_descriptor_data = f.read(2)
        # assert delayed_descriptor_data == b'\x82\xB1'
        # # Pick out a random point and verify the location
        # f.seek(257)
        # location_data = f.read(8)
        # assert location_data == b'\xCD\x54\xB0\x18\x10\xB0\xDF\x57'

        # # Verify that there are 157 profiles
        # f.seek(1862)
        # assert f.read(2) == b'\xBF\x3A'


@patch('bufrtools.encoding.wildlife_computers.parse_args')
def test_wildlife_computers_encoding_from_parquet(parse_args, tempfile_fixture):
    """Tests for encoding the wildlife computers profile data from a parquet file"""
    args = Namespace(
        output=Path(tempfile_fixture),
        profile_dataset=get_example_path('profile.parquet'),
        uuid='58112217efec720cd46e264e',
        ptt='160376'
    )
    parse_args.return_value = args
    wildlife_computers.main()

    with open(tempfile_fixture, 'rb') as f:
        file_id = f.read(4)
        assert file_id == b'BUFR'
        total_size = decoding.parse_unsigned_int(f.read(3), 24)
        assert total_size == 29218
        # f.seek(112)
        # # Verify that there are 88 points in the trajectory
        # delayed_descriptor_data = f.read(2)
        # assert delayed_descriptor_data == b'\x82\xB1'
        # # Pick out a random point and verify the location
        # f.seek(257)
        # location_data = f.read(8)
        # assert location_data == b'\xCD\x54\xB0\x18\x10\xB0\xDF\x57'

        # # Verify that there are 157 profiles
        # f.seek(1862)
        # assert f.read(2) == b'\xBF\x3A'


@patch('bufrtools.encoding.wildlife_computers.parse_args')
def test_wildlife_computers_encoding_from_csv(parse_args, tempfile_fixture):
    """Tests for encoding the wildlife computers profile data from a parquet file"""
    args = Namespace(
        output=Path(tempfile_fixture),
        profile_dataset=get_example_path('profile.csv'),
        uuid='58112217efec720cd46e264e',
        ptt='160376'
    )
    parse_args.return_value = args
    wildlife_computers.main()

    with open(tempfile_fixture, 'rb') as f:
        file_id = f.read(4)
        assert file_id == b'BUFR'
        total_size = decoding.parse_unsigned_int(f.read(3), 24)
        assert total_size == 29218
        # f.seek(112)
        # # Verify that there are 88 points in the trajectory
        # delayed_descriptor_data = f.read(2)
        # assert delayed_descriptor_data == b'\x82\xB1'
        # # Pick out a random point and verify the location
        # f.seek(257)
        # location_data = f.read(8)
        # assert location_data == b'\xCD\x54\xB0\x18\x10\xB0\xDF\x57'

        # # Verify that there are 157 profiles
        # f.seek(1862)
        # assert f.read(2) == b'\xBF\x3A'
