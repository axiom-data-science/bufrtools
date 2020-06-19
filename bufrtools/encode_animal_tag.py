#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Translates a JSON BUFR Message description for Animal Tags to a BUFR file."""
from pathlib import Path
from argparse import ArgumentParser
from bufrtools.util.bitmath import shift_uint, encode_uint
from bufrtools.util.parse import parse_ref
import io
import math
import yaml
import json
import sys
import pandas as pd
import numpy as np
import os


def encode_bufr(message: dict, context: dict):
    """Encodes a BUFR file based on the contents of message."""
    if 'buf' not in context:
        context['buf'] = io.BytesIO()
    encode_section0(message, context)
    encode_section1(message, context)
    encode_section3(message, context)
    encode_section4(message, context)
    encode_section5(context)
    finalize_bufr(context)


def finalize_bufr(context: dict):
    """Finalizes the BUFR message by writing the total size."""
    buf = context['buf']
    buf.seek(0, os.SEEK_END)
    total_len = buf.tell()
    buf.seek(4)
    total_len_b = shift_uint(total_len, 24, 0, 24)
    buf.write(total_len_b)
    buf.seek(0)


def encode_section0(message: dict, context: dict):
    """Encodes section0."""
    buf = context['buf']
    buf.write(b'BUFR')
    bufr_len_total = 0  # This number will be updated during finalization
    bufr_len_total_b = shift_uint(bufr_len_total, 24, 0, 24)
    buf.write(bufr_len_total_b)
    buf.write(b'\x04')  # Edition 4 is fixed


def encode_section1(message: dict, context: dict):
    """Encodes section1."""
    buf = context['buf']
    section1 = message['section1']
    start = buf.tell()
    section_len_total = 0  # This number will be updated during finalization
    buf.seek(start + 3)
    buf.write(b'\x00')  # BUFR Master Table 0
    originating_centre = shift_uint(section1['originating_centre'], 16, 0, 16)
    buf.write(originating_centre)
    sub_centre = shift_uint(section1['sub_centre'], 16, 0, 16)
    buf.write(sub_centre)
    seq_no = bytes([section1['seq_no']])
    buf.write(seq_no)
    buf.write(b'\x00')  # No section 2
    data_category = bytes([section1['data_category']])
    buf.write(data_category)
    sub_category = bytes([section1['sub_category']])
    buf.write(sub_category)
    local_category = bytes([section1['local_category']])
    buf.write(local_category)
    master_table_version = bytes([section1['master_table_version']])
    buf.write(master_table_version)
    local_table_version = bytes([section1['local_table_version']])
    buf.write(local_table_version)
    year = shift_uint(section1['year'], 16, 0, 16)
    buf.write(year)
    month = bytes([section1['month']])
    buf.write(month)
    day = bytes([section1['day']])
    buf.write(day)
    hour = bytes([section1['hour']])
    buf.write(hour)
    minute = bytes([section1['minute']])
    buf.write(minute)
    second = bytes([section1['second']])
    buf.write(second)
    end = buf.tell()
    buf.seek(start)
    section_len_total = end - start
    section_len_total_b = shift_uint(section_len_total, 24, 0, 24)
    buf.write(section_len_total_b)
    buf.seek(end)


def encode_section3(message: dict, context: dict):
    """Encodes section 3."""
    buf = context['buf']
    section3 = message['section3']
    start = buf.tell()
    buf.seek(start + 3)
    buf.write(b'\x00')  # Set to 0 per standard
    number_of_subsets = shift_uint(section3['number_of_subsets'], 16, 0, 16)
    buf.write(number_of_subsets)
    flags_byte = 0
    if section3['observed_flag']:
        flags_byte |= 0x80
    if section3['compressed_flag']:
        flags_byte |= 0x40
    buf.write(bytes([flags_byte]))

    for descriptor in section3['descriptors']:
        f, x, y = parse_ref(descriptor)
        fx = bytearray(1)
        fx = encode_uint(fx, f, 0, 2)
        fx = encode_uint(fx, x, 2, 6)
        buf.write(fx)
        buf.write(bytes([y]))

    end = buf.tell()
    section_len = end - start
    buf.seek(start)
    section_len_b = shift_uint(section_len, 24, 0, 24)
    buf.write(section_len_b)
    buf.seek(end)


def encode_section4(message: dict, context: dict):
    """Encodes section 4."""
    buf = context['buf']
    write_buf = io.BytesIO()
    start = buf.tell()
    buf.seek(start + 3)
    buf.write(b'\x00')

    bit_offset = 0
    sequence = message['section4'][:]
    override_bitlength = None
    for seq in sequence:
        print(seq)
        # Deal with operators
        if seq['type'] == 'operator':
            f, x, y = parse_ref(seq['fxy'])
            if (f, x) == (2, 8):
                if y > 0:
                    override_bitlength = y * 8
                else:
                    override_bitlength = None
            continue
        if seq['bit_len'] < 1:
            # Skip 0-length sections, they're for information purposes only
            continue
        if seq['type'] == 'numeric':
            bitlen = seq['bit_len']
            if override_bitlength:
                bitlen = override_bitlength
            value = float(seq['value'])
            if seq['scale']:
                value = value * math.pow(10, seq['scale'])
            if seq['offset']:
                value = value - seq['offset']
            # The value should be ROUNDED to the nearest integer
            value = int(np.round(value))
            write_uint(write_buf, value, bit_offset, bitlen)
            bit_offset += seq['bit_len']
        elif seq['type'] == 'string':
            bitlen = seq['bit_len']
            if override_bitlength:
                bitlen = override_bitlength
            write_ascii(write_buf, seq['value'], bit_offset, bitlen)
            bit_offset += seq['bit_len']

    write_buf.seek(0)
    buf.write(write_buf.read())
    # Write section length
    end = buf.tell()
    section_len = end - start
    section_len_b = shift_uint(section_len, 24, 0, 24)
    buf.seek(start)
    buf.write(section_len_b)
    buf.seek(end)


def encode_section5(context: dict):
    """Encodes section 5 into the Byte buffer."""
    buf = context['buf']
    buf.write(b'7777')


def write_uint(buf, value, bit_offset, bitlen):
    """Writes an unsgined integer to the buffer at `bit_offset` that occupies `bitlen` bits."""
    byte_start = bit_offset // 8
    r = bit_offset % 8
    byte_len = math.ceil((bitlen + r) / 8)
    data = bytearray(byte_len)
    buf.seek(byte_start)
    if r != 0:
        data[0] = buf.read(1)[0]
        buf.seek(byte_start)
    data = encode_uint(data, value, r, bitlen)
    buf.write(data)


def write_ascii(buf, data, bit_offset, bitlen):
    """Writes ASCII to the buffer with a bit offset."""
    ascii_encoded = data.rjust(bitlen // 8).encode('ascii')
    for i, value in enumerate(ascii_encoded):
        write_uint(buf, value, bit_offset + (i * 8), 8)


def main():
    """To fill out at some point."""
    parser = ArgumentParser(description=main.__doc__)
    parser.add_argument('-o',
                        '--output',
                        default='output.bufr',
                        type=Path,
                        help='Filename to output to.')
    parser.add_argument('-d', '--data', type=Path, help='Data (CSV, JSON, YAML)')
    parser.add_argument('descriptor',
                        type=Path,
                        help='A YAML or JSON file describing the message\'s global attributes.')
    args = parser.parse_args()

    descriptor = args.descriptor
    if descriptor.suffix == '.yml':
        msg = yaml.safe_load(descriptor.read_text('utf-8'))
    elif descriptor.suffix == '.json':
        msg = json.loads(descriptor.read_text('utf-8'))
    else:
        raise ValueError(f'Unknown descriptor format: {descriptor.suffix}')

    if args.data:
        if args.data.suffix == '.csv':
            df = pd.read_csv(args.data, dtype={'fxy': str, 'value': str, 'bit_len': np.uint16})
            section4 = df.to_dict(orient='records')
        elif args.data.suffix == '.json':
            section4 = json.loads(args.data.read_text('utf-8'))
        elif args.data.suffix == '.yml':
            section4 = yaml.load_safe(args.data.read_text('utf-8'))
        else:
            raise ValueError(f'Unknown data format: {args.data.suffix}')
        msg['section4'] = section4

    context = {}
    encode_bufr(msg, context)
    buf = context['buf']
    buf.seek(0)
    args.output.write_bytes(buf.read())
    return 0


if __name__ == '__main__':
    sys.exit(main())
