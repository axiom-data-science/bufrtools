#!/usr/bin/env pytest
#-*- coding: utf-8 -*-
"""Unit tests for wildlife computers."""
from bufrtools import decoding
from bufrtools.encoding import wildlife_computers
from pathlib import Path
import os
import tempfile
import bufrtools
import pytest
from unittest.mock import patch
from argparse import Namespace


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
def test_wildlife_computers_encoding(parse_args, tempfile_fixture):
    """Tests for encoding the wildlife computers profile data."""
    args = Namespace(output=Path(tempfile_fixture), profile_dataset=get_example_path('profile.nc'))
    parse_args.return_value = args
    wildlife_computers.main()

    with open(tempfile_fixture, 'rb') as f:
        file_id = f.read(4)
        assert file_id == b'BUFR'
        total_size = decoding.parse_unsigned_int(f.read(3), 24)
        assert total_size == 28159
        f.seek(112)
        # Verify that there are 88 points in the trajectory
        delayed_descriptor_data = f.read(2)
        assert delayed_descriptor_data == b'\x82\xB1'
        # Pick out a random point and verify the location
        f.seek(257)
        location_data = f.read(8)
        assert location_data == b'\xCD\x54\xB0\x18\x10\xB0\xDF\x57'

        # Verify that there are 157 profiles
        f.seek(1862)
        assert f.read(2) == b'\x3F\x3A'