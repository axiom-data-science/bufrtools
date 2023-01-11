#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Module for common BUFR encoding functions."""
import io
import os
import math

import numpy as np
from bufrtools.util.parse import parse_ref
from bufrtools.util.bitmath import shift_uint, encode_uint


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
        # Deal with operators
        if seq['type'] == 'operator':
            f, x, y = parse_ref(seq['fxy'])
            if (f, x) == (2, 8):
                if y > 0:
                    override_bitlength = y * 8
                else:
                    override_bitlength = None
            # This is a cancel code
            if (f, x, y) == (2, 1, 0):
                override_bitlength = None
            # Special case or is 129 always a change to 24?
            if (f, x, y) == (2, 1, 129):
                override_bitlength = 24
            continue
        if seq['bit_len'] < 1:
            # Skip 0-length sections, they're for information purposes only
            continue
        if seq['type'] == 'numeric':
            bitlen = seq['bit_len']
            if override_bitlength:
                bitlen = override_bitlength
            value = seq['value']
            if np.isnan(float(value)):
                # If a value is NaN, fill it with all 1s,
                # which is the BUFR missing_value. Do not
                # apply scale and offset
                value = float(int('1' * bitlen, 2))
            else:
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
            write_ascii(write_buf, str(seq['value']), bit_offset, bitlen)
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
