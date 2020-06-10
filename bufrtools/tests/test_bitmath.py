#!/usr/bin/env pytest
#-*- coding: utf-8 -*-
"""Unit tests for bitmath."""
from bufrtools.util.bitmath import encode_uint


def test_encode_uint():
    """Tests our ability to embed unsigned integers in a string of bytes."""
    a = b'\xcc\xdd\x88'
    b = 0x12
    r = encode_uint(a, b, 3, 14)
    assert r == b'\xc0\x09\x08'

    a = bytes([
        0xaa,
        0xaa,
        0xaa,
        0xaa,
    ])
    b = 0xf
    r = encode_uint(a, b, 0, 4)
    assert r == b'\xfa\xaa\xaa\xaa'
