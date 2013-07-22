# harvest rdf

import os
import glob
import rdflib
import requests
import sys
from urlparse import urlparse

try:
    from progressbar import ProgressBar, Bar, Percentage, ETA, SimpleProgress, Timer
except ImportError:
    ProgressBar = None

from belfastdata.rdfns import DC, SCHEMA_ORG


class HarvestRdf(object):

    URL_QUEUE = []
    PROCESSED_URLS = []
    total = 0
    harvested = 0
    errors = 0

    _serialize_opts = {}

    def __init__(self, urls, output_dir, find_related=False, verbosity=1,
                 format=None):
        self.URL_QUEUE.extend(urls)
        self.find_related = find_related
        self.base_dir = output_dir
        self.verbosity = verbosity

        self.format = format
        if format is not None:
            self._serialize_opts['format'] = format

        self.process_urls()

    def process_urls(self):
        if (len(self.URL_QUEUE) >= 5 or self.find_related) \
           and ProgressBar and os.isatty(sys.stderr.fileno()):
            widgets = [Percentage(), ' (', SimpleProgress(), ')',
                       Bar(), ETA()]
            progress = ProgressBar(widgets=widgets,
                                   maxval=len(self.URL_QUEUE)).start()
            processed = 0
        else:
            progress = None

        while self.URL_QUEUE:
            url = self.URL_QUEUE.pop(0)
            self.harvest_rdf(url)
            self.total += 1
            self.PROCESSED_URLS.append(url)
            if progress:
                progress.maxval = self.total + len(self.URL_QUEUE)
                progress.update(len(self.PROCESSED_URLS))

        if progress:
            progress.finish()

        # report if sufficient numbers:
        if self.verbosity >= 1 and (self.harvested > 5 or self.errors):
            print 'Processed %d url%s: %d harvested, %d error%s' % \
                  (len(self.PROCESSED_URLS),
                   '' if len(self.PROCESSED_URLS) == 1 else 's',
                   self.harvested, self.errors,
                   '' if self.errors == 1 else 's')

    def harvest_rdf(self, url):
        g = rdflib.Graph()
        try:
            response = requests.get(url, headers={'cache-control': 'no-cache'})
            data = g.parse(data=response.content, location=url, format='rdfa')
            # NOTE: this was working previously, and should be fine,
            # but now generates an RDFa parsing error / ascii codec error
            # data = g.parse(location=url, format='rdfa')
        except Exception as err:
            print 'Error attempting to load %s - %s' % (url, err)
            self.errors += 1
            return

        triple_count = len(data)
        # if no rdf data was found, report and return
        if triple_count == 0:
            if self.verbosity >= 1:
                print 'No RDFa data found in %s' % url
            return
        else:
            if self.verbosity > 1:
                print 'Parsed %d triples from %s' % (triple_count, url)

        filename = self.filename_from_url(url)
        if self.verbosity > 1:
            print 'Saving as %s' % filename
        with open(filename, 'w') as datafile:
            data.serialize(datafile, **self._serialize_opts)
        self.harvested += 1

        # if find related is true, look for urls related to this one
        # via either schema.org relatedLink or dcterms:hasPart
        queued = 0
        if self.find_related:
            orig_url = rdflib.URIRef(url)

            # find all sub parts of the current url (e.g., series and indexes)
            for subj, obj in data.subject_objects(predicate=DC.hasPart):
                if subj == orig_url or \
                   (subj, rdflib.OWL.sameAs, rdflib.URIRef(url)) in data:
                    related_url = unicode(obj)
                    # add to queue if not already queued or processed
                    if related_url not in self.URL_QUEUE or self.PROCESSED_URLS:
                        self.URL_QUEUE.append(related_url)
                        queued += 1

            # follow all related link relations
            for subj, obj in data.subject_objects(predicate=SCHEMA_ORG.relatedLink):
                # Technically, we may only want related links where
                # the subject is the current URL...
                # Currently, findingaids rdfa is putting that relation on the
                # archival collection object rather than the webpage object;
                # For now, go ahead and grab any relatedLink in the RDF.
                # if subj == orig_url or \
                #    (subj, rdflib.OWL.sameAs, rdflib.URIRef(url)) in data:
                related_url = unicode(obj)
                if related_url not in self.URL_QUEUE or self.PROCESSED_URLS:
                    self.URL_QUEUE.append(related_url)
                    queued += 1

        if queued and self.verbosity > 1:
            print 'Queued %d related URL%s to be harvested' % \
                  (queued, 's' if queued != 1 else '')

    def filename_from_url(self, url):
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
            #  NOTE: save as .rdf since it may or may not be rdf xml
            return os.path.join(self.base_dir, '%s.%s' % (filebase, self.format))


class HarvestRelated(object):

    # sources to be harvested
    sources = [
        # NOTE: using tuples to ensure we process in this order,
        # to allow harvesting dbpedia records referenced in viaf/geonames
        ('viaf', 'http://viaf.org/'),
        ('geonames', 'http://sws.geonames.org/'),
        ('dbpedia', 'http://dbpedia.org/'),
    ]

    _serialize_opts = {}

    def __init__(self, files, basedir, format=None):
        self.files = files
        self.basedir = basedir

        if format is not None:
            self._serialize_opts['format'] = format

        self.run()

    def run(self):
        graph = rdflib.Graph()

        # load all files into a single graph so we can query distinct
        g = rdflib.Graph()
        for infile in self.files:
            basename, ext = os.path.splitext(infile)
            fmt = ext.strip('.')
            try:
                g.parse(infile, format=fmt)
            except Exception as err:
                print "Error parsing '%s' as RDF -- %s" % (infile, err)
                continue

        for name, url in self.sources:
            # find anything that is a subject or object and has a
            # viaf, dbpedia, or geoname uri
            res = g.query('''
                SELECT DISTINCT ?uri
                WHERE {
                    { ?uri ?p ?o }
                UNION
                    { ?s ?p ?uri }
                FILTER regex(str(?uri), "^%s") .
                }
            ''' % url)
            print '%d %s URI%s' % (len(res), name,
                                   's' if len(res) != 1 else '')

            if len(res) == 0:
                continue

            uris = [unicode(r['uri']).encode('ascii', 'ignore') for r in res]

            datadir = os.path.join(self.basedir, name)
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
                # build filename based on URI
                baseid = u.rstrip('/').split('/')[-1]

                filename = os.path.join(datadir, '%s.rdf' % baseid)

                # if already downloaded, don't re-download but add to graph
                # for any secondary related content
                if os.path.exists(filename):
                    # TODO: better refinement would be to use modification
                    # time on the file to download if changed
                    # (do all these sources support if-modified-since headers?)
                    g.parse(location=filename)

                else:
                    # Use requests with content negotiation to load the data
                    data = requests.get(u, headers={'accept': 'application/rdf+xml'})
                    if data.status_code == requests.codes.ok:
                        # also add to master graph so we can download related data
                        # i.e.  dbpedia records for VIAF persons
                        g.parse(data=data.content)

                        tmp_graph = rdflib.Graph()
                        tmp_graph.parse(data=data.content)

                        with open(filename, 'w') as datafile:
#                            datafile.write(data.content)
                            tmp_graph.serialize(datafile, **self._serialize_opts)

            #                         with open(filename, 'w') as datafile:
            # data.serialize(datafile, **self._serialize_opts)
                    else:
                        print 'Error loading %s : %s' % (u, data.status_code)

                if progress:
                    processed += 1
                    progress.update(processed)

            if progress:
                progress.finish()
