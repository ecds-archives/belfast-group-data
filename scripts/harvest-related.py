#!/usr/bin/env python

# pip deps
# rdflib

import argparse
import os
import sys
import urllib2

try:
    import rdflib
    import requests
except ImportError:
    print '''Please install rdflib and requests (pip install or easy_install rdflib requests)'''
    exit(-1)


try:
    from progressbar import ProgressBar, Bar, Percentage, ETA, SimpleProgress, Timer
except ImportError:
    ProgressBar = None
    print '''Optionally install progressbar (pip install or easy_install progressbar)'''


def process_files(files, basedir):
    # load all files into a single graph so we can query distinct
    g = rdflib.Graph()
    for infile in files:
        try:
            g.parse(infile)
        except Exception as err:
            print "Error parsing '%s' as RDF -- %s" % (infile, err)
            continue

    resources = [
        # NOTE: using tuples to ensure we process in this order,
        # to allow harvesting dbpedia records referenced in viaf/geonames
        ('viaf', 'http://viaf.org/'),
        ('geonames', 'http://sws.geonames.org/'),
        ('dbpedia', 'http://dbpedia.org/'),
    ]

    for name, url in resources:
        # anything that is a subject or object and has a
        # viaf, dbpedia, or geoname uri
        res = g.query('''
            SELECT DISTINCT ?uri
            WHERE {
            {?uri ?p ?o }
            UNION
            {?s ?p ?uri }
            FILTER regex(str(?uri), "^%s") .
            }
            ''' % url)
        print '%d %s URI%s' % (len(res), name,
                               's' if len(res) != 1 else '')

        if len(res) == 0:
            continue

        uris = [str(r['uri']) for r in res]

        datadir = os.path.join(basedir, name)
        if not os.path.isdir(datadir):
            os.mkdir(datadir)

        if len(uris) >= 5 and ProgressBar and os.isatty(sys.stderr.fileno()):
            widgets = [Percentage(), ' (', SimpleProgress(), ')',
                       Bar(), ETA()]
            progress = ProgressBar(widgets=widgets, maxval=len(uris)).start()
            processed = 0
        else:
            progress = None

        for u in uris:
            # build filename based on viaf id
            baseid = u.rstrip('/').split('/')[-1]
            filename = os.path.join(datadir, '%s.rdf' % baseid)

            # Use requests with content negotiation to load the data
            data = requests.get(u, headers={'accept': 'application/rdf+xml'})
            if data.status_code == requests.codes.ok:
                # also add to master graph so we can download related data
                # i.e.  dbpedia records for VIAF persons
                g.parse(data=data.content)

                with open(filename, 'w') as datafile:
                    datafile.write(data.content)
            else:
                print 'Error loading %s : %s' % (u, data.status_code)

            if progress:
                processed += 1
                progress.update(processed)

        if progress:
            progress.finish()


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