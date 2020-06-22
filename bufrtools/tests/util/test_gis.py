#!/usr/bin/env pytest
#-*- coding: utf-8 -*-
"""Unit tests for wildlife computers encoders."""
import numpy as np
from bufrtools.util.gis import azimuth, haversine_distance


def test_haversin_distance():
    """Tests that the haversin great circle distance calculations are correct."""
    x = np.array([
        -5.714722222222222,
        3.0700000000000003,
    ])
    y = np.array([
        50.06638888888889,
        58.64388888888889,
    ])

    distance = haversine_distance(x * np.pi / 180, y * np.pi / 180)
    np.testing.assert_almost_equal(distance[0], 1109921.95, 3)


def test_azimuth():
    """Tests that the great circle distance azimuth calculations are correct."""
    x = np.array([
        -5.714722222222222,
        3.0700000000000003,
    ])
    y = np.array([
        50.06638888888889,
        58.64388888888889,
    ])

    theta = azimuth(x * np.pi / 180, y * np.pi / 180) * 180 / np.pi
    np.testing.assert_almost_equal(theta[0], 27.3216, 3)
