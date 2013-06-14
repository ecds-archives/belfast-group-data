#!/usr/bin/env python

# pip deps
# rdflib

import os
import argparse
import urllib2

try:
    import rdflib
except ImportError:
    print '''Please install rdflib (pip install or easy_install rdflib)'''
    exit(-1)


def process_files(files, basedir):
    # load all files into a single graph so we can query distinct
    g = rdflib.Graph()
    for infile in files:
        try:
            g.parse(infile)
        except Exception as err:
            print "Error parsing '%s' as RDF -- %s" % (infile, err)
            continue

    resources = {
        'viaf': 'http://viaf.org/',
        'dbpedia': 'http://dbpedia.org/',
        'geonames': 'http://sws.geonames.org/',
        # possibly use a regex for geonames variants?
    }

    for name, url in resources.iteritems():
        res = g.query('''
            SELECT DISTINCT ?s
            WHERE {
            ?s ?p ?o .
            FILTER regex(str(?s), "^%s") .
            }
            ''' % url)
        print '%d %s URI%s' % (len(res), name,
                               's' if len(res) != 1 else '')

        if len(res) == 0:
            continue

        uris = [str(r['s']) for r in res]

        datadir = os.path.join(basedir, name)
        if not os.path.isdir(datadir):
            os.mkdir(datadir)

        # TODO: progressbar would be nice
        for u in uris:
            # build filename brased on viaf id
            baseid = u.rstrip('/').split('/')[-1]
            filename = os.path.join(datadir, '%s.rdf' % baseid)
            # Use rdflib to load the data - should handle content negotation, etc
            data = rdflib.Graph()
            try:
                data.parse(u)
            except urllib2.HTTPError:
                print 'Error loading %s' % u
                continue

            with open(filename, 'w') as datafile:
                data.serialize(datafile)


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

    process_files(args.files, args.output)