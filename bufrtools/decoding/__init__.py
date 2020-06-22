#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Package for some decoding utilities."""
import logging

from bufrtools.tables import get_code_table_figure

log = logging.getLogger(__name__)


def read_bytes_bitlen(data: bytes, offset_bits: int, bitlen: int):
    """Read a set of bytes for an exact bitlength and a specific bit offset."""
    count = 0
    first_bitmask = ((1 << (8 - offset_bits)) - 1)
    second_bitmask = 0xff ^ first_bitmask
    values = []
    while count < (((bitlen - 1) // 8) + 1):
        value = (data[count] & first_bitmask) << (offset_bits)
        if second_bitmask and (count * 8 + (8 - offset_bits)) < bitlen:
            value = value | ((data[count + 1] & second_bitmask) >> (8 - offset_bits))
        values.append(value)
        count += 1
    return bytes(values)


def parse_unsigned_int(data: bytes, bitlen: int):
    """Parses an unsigned integer from data that is `bitlen` bits long."""
    val = '0b' + ''.join([f'{b:08b}' for b in data])
    return int(val[0:2 + bitlen], 2)


def decode_empty(context: dict,
                 bit_offset: int,
                 bit_len: int,
                 text: str,
                 fxy: str,
                 value: str = None) -> dict:
    """Returns a tag to represent an empty space or missing value."""
    start = bit_offset // 8
    r = bit_offset % 8
    byte_len = (bit_len + r) // 8 + 1
    retval = {
        'text': text,
        'offset': context['offset'] + start,
        'length': byte_len,
        'type': 'other',
        'fxy': fxy,
    }
    if value is not None:
        retval['value'] = value
    return retval


def decode_numeric(data: bytes,
                   context: dict,
                   bit_offset: int,
                   bit_len: int,
                   text: str,
                   scale: float = None,
                   offset: float = None,
                   fxy: str = None,
                   code_table: bool = False) -> dict:
    """Decodes a numeric data field."""
    start = bit_offset // 8
    r = bit_offset % 8
    byte_len = (bit_len + r) // 8 + 1
    raw = read_bytes_bitlen(
        data[start:start + byte_len],
        r,
        bit_len)
    value = parse_unsigned_int(raw, bit_len)
    if offset is not None:
        value = offset + value
    if scale is not None:
        value = value / (10 ** scale)
    log.debug(f'Decoded value {value}')
    if code_table:
        try:
            code_figure = get_code_table_figure(fxy, int(value))
            value = f'{value:0.0f} ({code_figure["EntryName_en"]})'
        except Exception:
            log.warning(f'Unable to find code table value for {fxy}')
    return {
        'text': text,
        'offset': context['offset'] + start,
        'length': byte_len,
        'type': 'other',
        'value': value,
        'fxy': fxy,
        'bit_offset': bit_offset,
    }


def decode_ccit(data: bytes,
                context: dict,
                bit_offset: int,
                bit_len: int,
                text: str,
                fxy: str = None) -> dict:
    """Decodes an ASCII field."""
    start = bit_offset // 8
    r = bit_offset % 8
    byte_len = (bit_len + r) // 8 + 1
    raw = read_bytes_bitlen(
        data[start:start + byte_len],
        r,
        bit_len)
    ascii_value = 'INVALID'
    try:
        ascii_value = raw.decode('ascii').strip()
    except UnicodeDecodeError:
        pass
    return {
        'text': text,
        'offset': context['offset'] + start,
        'length': byte_len,
        'type': 'string',
        'value': ascii_value,
        'fxy': fxy,
        'bit_offset': bit_offset,
    }
