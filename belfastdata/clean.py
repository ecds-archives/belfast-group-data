import hashlib
import rdflib
from rdflib import collection as rdfcollection
from django.utils.text import slugify

from belfastdata.rdfns import BIBO, DC, SCHEMA_ORG, BELFAST_GROUP_URI


class SmushGroupSheets(object):

    # base identifier for 'smushed' ids
    BELFASTGROUPSHEET = rdflib.Namespace("http://belfastgroup.org/groupsheets/md5/")

    def __init__(self, files):
        for f in files:
            self.process_file(f)

    def calculate_uri(self, uri, graph):
        # calculate a 'smushed' uri for a single groupsheet
        titles = []
        title = graph.value(uri, DC.title)

        # title is either a single literal OR an rdf sequence
        if title:
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

        # ignore title order for the purposes of de-duping
        # - sort titles so we can get a consistent MD5
        #   (assumes any group sheet with the same titles in any order
        #    and the same author is equivalent)
        # - slugify titles so we can ignore discrepancies in case and punctuation
        titles = sorted([slugify(t) for t in titles])

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

        return self.BELFASTGROUPSHEET[m.hexdigest()]

    def process_file(self, filename):
        # build a dictionary of "smushed" URIs for belfast group sheets
        # for this document
        new_uris = {}

        g = rdflib.Graph()
        g.parse(filename)

        # Find every manuscript mentioned in a document
        # that is *about* the belfast group
        # TODO: will also need to find ms associated with / presented at BG
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
        # FIXME: not finding group sheets in irishmisc! (no titles?)

        # if no manuscripts are found, stop and do not update the file
        if len(res) == 0:
            # possibly print out in a verbose mode if we add that
            #print 'No groupsheets found in %s' % filename
            return

        print 'Found %d possible groupsheets in %s' % (len(res), filename)

        for r in res:
            # FIXME: only calculate a new uri for blank nodes?
            newURI = self.calculate_uri(r['ms'], g)
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

