#!/usr/bin/env python

import argparse

from belfastdata.clean import SmushGroupSheets


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='De-dupe Belfast Group sheets by smushing URIs'
    )
    parser.add_argument('files', metavar='FILE', nargs='+',
                        help='files to be processed')
    args = parser.parse_args()
    SmushGroupSheets(args.files)
