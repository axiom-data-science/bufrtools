#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Module for GIS utility functions."""
import numpy as np


def haversine_distance(x, y, r=6378137.):
    """Returns the great-circle distance computed with haversine for the given trajectory.

    This function returns the distances formed between each set of points in x and y. The return
    value has the same shape as x, with the last value being 0.

    The equation used is:
             d
    haversin(-) = haversin(φ₂-φ₁)+ [cos(φ₁) cos(φ₂) haversin(λ₂-λ₁)]
             r

    Where haversin(x) = sin²(x/2)


    Arguments:
        x (np.ndarray): Longitude values in radians
        y (np.ndarray): Latitude values in radians
        r (float): Radius of the earth.

    Returns:
        np.ndarray: Distances in the units of r.

    """
    dx = np.diff(x)
    dy = np.diff(y)
    sin2_phi = np.power(np.sin(dy / 2), 2)
    cos = np.cos(y[:-1]) * np.cos(y[1:])
    sin2_lambda = np.power(np.sin(dx / 2), 2)
    return 2 * r * np.arcsin(np.sqrt(sin2_phi + cos * sin2_lambda))


def azimuth(x, y):
    """Returns the azimuth of determined by the pair of coordinates.

    This function returns the azimuth formed for each pair of points in the trajectory specified by
    x and y. The return value will possess the same shape as x, the last value will be 0.

    The equation used is derived from the spherical law of sines

    sin A   sin B
    ----- = -----
    sin a   sin b

    Where A is the angle of the difference in longitude values. B is the azimuth formed by the two
    points. b is the arc-distance formed by the geodesic from the second point to the north pole on
    a unit-sphere. a is the arc-distance of the geodesic formed from the intersection of the two
    points.

    Arguments:
        x (np.ndarray): Longitude values in radians
        y (np.ndarray): Latitude values in radians
        r (float): Radius of the earth.

    Returns:
        np.ndarray: Angles of azimuth.

    """
    theta = np.zeros_like(x)
    dx = np.diff(x)
    cos_phi = np.cos(y[1:])
    sin_d_lam = np.sin(dx)
    a = haversine_distance(x, y, 1)
    sin_a = np.sin(a)
    theta[:-1] = np.arcsin(cos_phi * sin_d_lam / sin_a)
    return theta
