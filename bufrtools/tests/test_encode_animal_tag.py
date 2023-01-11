#!/usr/bin/env pytest
#-*- coding: utf-8 -*-
"""Integration tests for encoding an animal tag."""
import os
import tempfile
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch

import pytest

import bufrtools
from bufrtools import decoding, encode_animal_tag


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


@patch('bufrtools.encode_animal_tag.parse_args')
def test_encode_animal_tag(parse_args, tempfile_fixture):
    """Tests that the basic encoding of YML descriptor sequences works."""
    basic_bufr = get_example_path('basic-atn.yml')
    args = Namespace(data=None, descriptor=basic_bufr, output=Path(tempfile_fixture))
    parse_args.return_value = args
    encode_animal_tag.main()

    with open(tempfile_fixture, 'rb') as f:
        file_id = f.read(4)
        assert file_id == b'BUFR'
        total_size = decoding.parse_unsigned_int(f.read(3), 24)
        assert total_size == 174
        f.seek(37)
        descriptor_data = f.read(2)
        fxy_f = descriptor_data[0] >> 6
        fxy_x = descriptor_data[0] & 0x3F
        fxy_y = descriptor_data[1]
        # Assert that the descriptor is 3-15-023 Animal Tagged data
        assert fxy_f == 3
        assert fxy_x == 15
        assert fxy_y == 23

        # Check sea water temperature value
        # f.seek(150)
        # temp_section_data = f.read(4)
        # assert temp_section_data == b'\x5b\x19\x4c\x40'


@patch('bufrtools.encode_animal_tag.parse_args')
def test_encode_with_csv(parse_args, tempfile_fixture):
    """Tests that the encoding using a CSV data file works."""
    basic_bufr = get_example_path('basic-atn.yml')
    example_data = get_example_path('example-profile.csv')
    args = Namespace(data=example_data, descriptor=basic_bufr, output=Path(tempfile_fixture))
    parse_args.return_value = args
    encode_animal_tag.main()

    with open(tempfile_fixture, 'rb') as f:
        file_id = f.read(4)
        assert file_id == b'BUFR'
        total_size = decoding.parse_unsigned_int(f.read(3), 24)
        assert total_size == 188

        f.seek(37)
        descriptor_data = f.read(2)
        fxy_f = descriptor_data[0] >> 6
        fxy_x = descriptor_data[0] & 0x3F
        fxy_y = descriptor_data[1]
        # Assert that the descriptor is 3-15-023 Animal Tagged data
        assert fxy_f == 3
        assert fxy_x == 15
        assert fxy_y == 23

        # f.seek(118)
        # lat_lon_data = f.read(8)
        # assert lat_lon_data == b'\xF3\x23\xF7\xA0\xA5\xAB\x0E\x88'

        # # Check sea water temp
        # f.seek(130)
        # sea_temp_data = f.read(4)
        # assert sea_temp_data == b'\x02\x2B\x5A\x7C'
        # context = {
        #     'offset': 130,
        # }
        # numeric_ctx = decoding.decode_numeric(sea_temp_data, context, 6, 19, '', 3, 0, '022045')
        # assert numeric_ctx['value'] == 284.34

        # # Check profile temp
        # f.seek(163)
        # sea_temp_data = f.read(3)
        # assert sea_temp_data == b'\x3b\xc4\x8b'
