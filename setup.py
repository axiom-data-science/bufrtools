#!/usr/bin/env python
#-*- coding: utf-8 -*-

from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


def pip_requirements():
    reqs = []
    with open('requirements.txt', 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            if line:
                reqs.append(line)
    return reqs


setup(
    name             = 'metar',
    version          = '0.0.1',
    description      = 'A command line utility to display METAR data.',
    long_description = readme(),
    author           = 'Luke Campbell',
    author_email     = 'luke@axds.co',
    url              = 'https://git.axiom/luke/metar',
    packages         = find_packages(),
    install_requires = pip_requirements(),
    entry_points     = {
        'console_scripts': [
            'metar = metar.cli:main',
        ],
    },
)


