# harvest rdf

import os
import rdflib
import requests
from urlparse import urlparse

# todo: move to common location
DCTERMS = rdflib.Namespace('http://purl.org/dc/terms/')
SCHEMA_ORG = rdflib.Namespace('http://schema.org/')


class HarvestRdf(object):

    URL_QUEUE = []
    PROCESSED_URLS = []
    total = 0
    errors = 0

    def __init__(self, urls, output_dir, find_related=False):
        self.URL_QUEUE.extend(urls)
        self.find_related = find_related
        self.base_dir = output_dir

    def process_urls(self):
        while self.URL_QUEUE:
            url = self.URL_QUEUE.pop(0)
            self.harvest_rdf(url)
            self.PROCESSED_URLS.append(url)

        # report if sufficient numbers:
        if (self.total > 5 or self.errors):
            print 'Processed %d url%s: %d harvested, %d error%s' % \
                  (len(self.PROCESSED_URLS),
                   '' if len(self.PROCESSED_URLS) == 1 else 's',
                   self.total, self.errors,
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
            # FIXME: don't exit here!
            print 'Error attempting to load %s - %s' % (url, err)
            self.errors += 1
            return

        triple_count = len(data)
        # if no rdf data was found, report and return
        if triple_count == 0:
            print 'No RDFa data found in %s' % url
            return
        else:
            print 'Parsed %d triples from %s' % (triple_count, url)

        filename = self.filename_from_url(url)
        print 'Saving as %s' % filename
        with open(filename, 'w') as datafile:
            data.serialize(datafile)
        self.total += 1

        # if find related is true, look for urls related to this one
        # via either schema.org relatedLink or dcterms:hasPart
        queued = 0
        if self.find_related:
            orig_url = rdflib.URIRef(url)

            # find all sub parts of the current url (e.g., series and indexes)
            for subj, obj in data.subject_objects(predicate=DCTERMS.hasPart):
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

        if queued:
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
            return os.path.join(self.base_dir, '%s.xml' % filebase)
