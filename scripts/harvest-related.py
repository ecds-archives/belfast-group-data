#!/usr/bin/env python

# pip deps
# rdflib

import argparse

from belfastdata.harvest import HarvestRelated

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Harvest related RDF from VIAF, DBpedia, and GeoNames'
    )
    parser.add_argument('files', metavar='FILE', nargs='+',
                        help='files to be processed')
    parser.add_argument('-o', '--output', metavar='DIR',
                        help='base directory for harvested content',
                        required=True)
    args = parser.parse_args()
    HarvestRelated(args.files, args.output)
