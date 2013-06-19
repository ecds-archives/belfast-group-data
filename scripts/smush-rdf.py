#!/usr/bin/env python

import argparse
import hashlib
import rdflib
from django.utils.text import slugify


BIBO = rdflib.Namespace('http://purl.org/ontology/bibo/')
DC = rdflib.Namespace('http://purl.org/dc/terms/')
SCHEMA_ORG = rdflib.Namespace('http://schema.org/')

BELFAST_GROUP_URI = 'http://viaf.org/viaf/123393054/'

# foaf smushing example - stable identifier
STABLE = rdflib.Namespace("http://example.com/person/mbox_sha1sum/")
BELFASTGROUPSHEET = rdflib.Namespace("http://belfastgroup.org/groupsheets/md5/")

# build a dictionary of stable URIs for belfast group sheets
# newURI = {}  # old subject : stable uri
# for s, p, o in g.triples((None, FOAF['mbox_sha1sum'], None)):
#     newURI[s] = STABLE[o]


def calculate_uri(uri, graph):
    titles = []
    title = graph.value(uri, DC.title)

    # title is either a single literal OR an rdf sequence
    if graph.value(DC.title) is not None:
        title = graph.value(DC.title)
        # single literal
        if isinstance(title, rdflib.Literal):
            titles.append(title)

        # otherwise, assuming node is an rdf sequence
        else:
            # convert from resource to standard blank node
            # since collection doesn't seem to handle resource
            # create a collection to allow treating as a list
            titles.extend(rdfcollection.Collection(graph,
                                                   title))
    # current RDF format is *not* preserving title order
    # sort them to get consistent MD5
    # (assumes any group sheet with the same titles in any order
    # and the same author is equivalent)

    titles = sorted([slugify(t) for t in titles])

    # due to vagaries of capitalization,

    author = graph.value(uri, SCHEMA_ORG.author)
    # blank node for the author is unreliable...
    if isinstance(author, rdflib.BNode):
        # This should mostly only occur in Queen's University Belfast,
        # where we don't have URIs but *do* have first & last names.
        # Construct lastname, first for author identifier
        # (Assumes we are using a VIAF URI wherever possible, which
        # should be the case.)
        last = graph.value(author, SCHEMA_ORG.familyName)
        first = graph.value(author, SCHEMA_ORG.givenName)
        if last is not None and first is not None:
            author = '%s, %s' % (last, first)
        else:
            author = None

    # if not at least one title or title and author, skip this ms
    if not titles and not author:
        return

    m = hashlib.md5()
    if author is None:
        author = 'anonymous'

    text = '%s %s' % (author, ' '.join(titles))
    m.update(text.encode('utf-8'))

    return BELFASTGROUPSHEET[m.hexdigest()]


def process_file(filename):
    # dictionary of "smushed" URIs for belfast group sheets
    # for this document
    new_uris = {}

    g = rdflib.Graph()
    g.parse(filename)

    # Find every manuscript mentioned in a document
    # that is *about* the belfast group
    # NOTE: need a way to filter non-belfast group content
    res = g.query('''
        PREFIX schema: <%s>
        PREFIX rdf: <%s>
        PREFIX bibo: <%s>
        SELECT ?ms
        WHERE {
            ?doc schema:about <%s> .
            ?doc schema:mentions ?ms .
            ?ms rdf:type bibo:Manuscript .
        }
        ''' % (rdflib.XSD, rdflib.RDF, BIBO, BELFAST_GROUP_URI)
    )
    # TODO: how to filter out non-group sheet irish misc content?
    # FIXME: not finding anything in irishmisc!

    # if no manuscripts are found, stop and do not update the file
    if len(res) == 0:
        # possibly print out in a verbose mode if we add that
        #print 'No groupsheets found in %s' % filename
        return

    print 'Found %d possible groupsheets in %s' % (len(res), filename)

    for r in res:
        # FIXME: print only do for blank nodes?
        newURI = calculate_uri(r['ms'], g)
        if newURI is not None:
            new_uris[r['ms']] = newURI

    output = rdflib.Graph()
    # bind namespace prefixes from the input graph
    for prefix, ns in g.namespaces():
        output.bind(prefix, ns)
    # iterate over all triples in the old graph and convert
    # any uris in the new_uris dictionary to the smushed identifier
    for s, p, o in g:
        s = new_uris.get(s, s)
        o = new_uris.get(o, o)
        output.add((s, p, o))

    # NOTE: currently replaces the starting file.  Might not be ideal,
    # but may actually be reasonable for the currently intended use.
    print 'Replacing %s' % filename
    with open(filename, 'w') as datafile:
        output.serialize(datafile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='De-dupe Belfast Group sheets by smushing URIs'
    )
    parser.add_argument('files', metavar='FILE', nargs='+',
                        help='files to be processed')
    args = parser.parse_args()
    for f in args.files:
        process_file(f)
