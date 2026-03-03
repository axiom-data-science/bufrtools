#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Datetime utility functions."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Returns the current UTC time as a naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
