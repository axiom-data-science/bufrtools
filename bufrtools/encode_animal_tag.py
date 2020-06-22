#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Translates a JSON BUFR Message description for Animal Tags to a BUFR file."""
import sys
import json
from typing import List
from pathlib import Path
from argparse import Namespace, ArgumentParser

import yaml
import numpy as np
import pandas as pd
from bufrtools.encoding.bufr import encode_bufr


def parse_args(argv: List[str]) -> Namespace:
    """Returns an argument namespace argument parsed from the command line arguments."""
    parser = ArgumentParser(description=main.__doc__)
    parser.add_argument('-o',
                        '--output',
                        default='output.bufr',
                        type=Path,
                        help='Filename to output to.')
    parser.add_argument('-d', '--data', type=Path, help='Data (CSV, JSON, YAML)')
    parser.add_argument('descriptor',
                        type=Path,
                        help='A YAML or JSON file describing the message\'s global attributes.')
    args = parser.parse_args(argv)
    return args


def main():
    """To fill out at some point."""
    args = parse_args(sys.argv[1:])
    descriptor = args.descriptor
    if descriptor.suffix == '.yml':
        msg = yaml.safe_load(descriptor.read_text('utf-8'))
    elif descriptor.suffix == '.json':
        msg = json.loads(descriptor.read_text('utf-8'))
    else:
        raise ValueError(f'Unknown descriptor format: {descriptor.suffix}')

    if args.data:
        if args.data.suffix == '.csv':
            df = pd.read_csv(args.data, dtype={'fxy': str, 'value': str, 'bit_len': np.uint16})
            section4 = df.to_dict(orient='records')
        elif args.data.suffix == '.json':
            section4 = json.loads(args.data.read_text('utf-8'))
        elif args.data.suffix == '.yml':
            section4 = yaml.load_safe(args.data.read_text('utf-8'))
        else:
            raise ValueError(f'Unknown data format: {args.data.suffix}')
        msg['section4'] = section4

    context = {}
    encode_bufr(msg, context)
    buf = context['buf']
    buf.seek(0)
    args.output.write_bytes(buf.read())
    return 0


if __name__ == '__main__':
    sys.exit(main())
