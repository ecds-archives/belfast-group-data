#!/usr/bin/env python

# pip deps
# rdflib

from urlparse import urlparse
import argparse
try:
    import rdflib
    import requests
except ImportError:
    print '''Please install rdflib and/or requests (pip install or easy_install rdflib requests)'''
    exit(-1)

DCTERMS = rdflib.Namespace('http://purl.org/dc/terms/')
SCHEMA_ORG = rdflib.Namespace('http://schema.org/')

URL_QUEUE = []
PROCESSED_URLS = []


def harvest_rdf(url, find_related=False):
    g = rdflib.Graph()
    try:
        response = requests.get(url, headers={'cache-control': 'no-cache'})
        data = g.parse(data=response.content, location=url, format='rdfa')
        # NOTE: this was working previously, and should be fine,
        # but now generates an RDFa parsing error / ascii codec error
        # data = g.parse(location=url, format='rdfa')
    except Exception as err:
        print 'Error attempting to load %s - %s' % (url, err)
        exit(-1)

    triple_count = len(data)
    # if no rdf data was found, report and return
    if triple_count == 0:
        print 'No RDFa data found in %s' % url
        return
    else:
        print 'Parsed %d triples from %s' % (triple_count, url)

    filename = filename_from_url(url)
    print 'Saving as %s' % filename
    with open(filename, 'w') as datafile:
        data.serialize(datafile)

    # if find related is true, look for urls related to this one
    # via either schema.org relatedLink or dcterms:hasPart
    queued = 0
    if find_related:
        orig_url = rdflib.URIRef(url)

        # find all sub parts of the current url (e.g., series and indexes)
        for subj, obj in data.subject_objects(predicate=DCTERMS.hasPart):
            if subj == orig_url or \
               (subj, rdflib.OWL.sameAs, rdflib.URIRef(url)) in data:
                related_url = unicode(obj)
                if related_url not in URL_QUEUE or PROCESSED_URLS:
                    URL_QUEUE.append(related_url)
                    queued += 1

        # find all sub parts of the current url (e.g., series and indexes)
        for subj, obj in data.subject_objects(predicate=SCHEMA_ORG.relatedLink):
            # Technically, we may only want related links where
            # the subject is the current URL...
            # Currently, findingaids rdfa is putting that relation on the
            # archival collection object rather than the webpage object;
            # For now, go ahead and grab any relatedLink in the RDF.
            # if subj == orig_url or \
            #    (subj, rdflib.OWL.sameAs, rdflib.URIRef(url)) in data:
            related_url = unicode(obj)
            if related_url not in URL_QUEUE or PROCESSED_URLS:
                URL_QUEUE.append(related_url)
                queued += 1

        if queued:
            print 'Queued %d related URL%s to be harvested' % \
                  (queued, 's' if queued != 1 else '')


def absolute_url(url):
    # argparse type helper to validate url input
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        msg = 'An absolute URL is required'
        raise argparse.ArgumentTypeError(msg)
    return parsed_url.geturl()


def filename_from_url(url):
    # generate a filename based on the url (simple version)
    # NOTE: doesn't handle query string parameters, etc
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    host = host.replace('.', '_').replace(':', '-')
    path = parsed_url.path
    path = path.strip('/').replace('/', '-')
    filebase = host
    if path:
        filebase += '_%s' % path
    return '%s.xml' % filebase


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Harvest RDFa from a specified URL')
    parser.add_argument('url', metavar='URL', type=absolute_url,
                        help='URL where RDFa should be harvested')
    parser.add_argument('--related', action='store_true',
                        help='Harvest RDFa from related urls')
    # NOTE: could support multiple input urls...
    # TODO: verbosity setting?
    args = parser.parse_args()
    URL_QUEUE.append(args.url)

    while URL_QUEUE:
        url = URL_QUEUE.pop(0)
        harvest_rdf(url, find_related=args.related)
        PROCESSED_URLS.append(url)
