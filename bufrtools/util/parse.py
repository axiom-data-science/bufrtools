#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Module for basic and general parsing functions."""


def parse_ref(fxy) -> tuple:
    """Returns a tuple of the FXXYYYY string parsed out into integers."""
    f = int(fxy[0])
    x = int(fxy[1:3])
    y = int(fxy[3:6])
    return f, x, y
