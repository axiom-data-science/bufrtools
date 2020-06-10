#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Utility functions for bit mangling."""


def shift_uint(value: int, full_bitlength: int, bit_offset: int, bitlen: int) -> bytes:
    """Shifts an unsigned integer and returns the byte array of the shifted value."""
    shift = full_bitlength - bitlen - bit_offset
    output = bytearray(full_bitlength // 8)
    for i in range(len(output)):
        byteshift = full_bitlength - ((i + 1) * 8)
        relshift = shift - byteshift
        if relshift < 0:
            output[i] = 0xFF & (value >> (-relshift))
        elif relshift < 8:
            output[i] = 0XFF & (value << relshift)
    return output


def encode_uint(data: bytes, value: int, bit_offset: int, bitlen: int) -> bytearray:
    """Returns a bytearray that embeds the value in the stream of bytes.

    This function embeds the unsigned integer `value` in `data` after `bit_offset` bits and ensures
    that `value` occupies `bitlen` bits.
    """
    full_bitlength = len(data) * 8
    mask = shift_uint((1 << bitlen) - 1, full_bitlength, bit_offset, bitlen)
    shifted_value = shift_uint(value, full_bitlength, bit_offset, bitlen)
    output = bytearray(len(data))
    for i in range(len(data)):
        output[i] = data[i] ^ ((data[i] ^ shifted_value[i]) & mask[i])

    return output
