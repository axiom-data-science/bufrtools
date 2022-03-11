#!/usr/bin/env python
#-*- coding: utf-8 -*-

from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


def version():
    with open('VERSION') as f:
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
    name             = 'bufrtools',
    version          = version(),
    description      = 'A suite of tools for working with BUFR',
    long_description = readme(),
    long_description_content_type = 'text/markdown',
    author           = 'Luke Campbell',
    author_email     = 'luke@axds.co',
    url              = 'https://github.com/axiom-data-science/bufrtools',
    packages         = find_packages(),
    install_requires = pip_requirements(),
    entry_points     = {
        'console_scripts': [
        ],
    },
    package_data     = {
        'bufrtools.tables' : ['data/*.csv'],
    },
)
