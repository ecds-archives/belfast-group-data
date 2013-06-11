#!/usr/bin/env python

# pip deps
# rdflib

import argparse
import re
import os.path
try:
    import rdflib
except ImportError:
    print '''Please install rdflib (pip install or easy_install rdflib)'''
    exit(-1)
try:
    from bs4 import BeautifulSoup
except ImportError:
    print '''Please install BeautifulSoup4 (pip install or easy_install BeautifulSoup4)'''
    exit(-1)

# rdf namespaces
ARCH = rdflib.Namespace('http://purl.org/archival/vocab/arch#')
SCHEMA_ORG = rdflib.Namespace('http://schema.org/')
DC = rdflib.Namespace('http://purl.org/dc/terms/')
DCMITYPE = rdflib.Namespace('http://purl.org/dc/dcmitype/')
BIBO = rdflib.Namespace('http://purl.org/ontology/bibo/')

# regex to grab names from description
NAME_REGEX = re.compile('(?P<last>[A-Z][a-zA-Z]+), (?P<first>[A-Z][a-z. ]+)')
DATE_REGEX = re.compile('Dated (?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{4})')
YEAR_REGEX = re.compile('Dates [^\d]*(?P<year>\d{4})')
PAGES_REGEX = re.compile('Typescripts?, (?P<num>\d)(p|pp.)')


NAME_URIS = {
    'Terry, Arthur': 'http://viaf.org/viaf/2490119/',
    'Hobsbaum, Philip': 'http://viaf.org/viaf/91907300/',
    'Heaney, Seamus': 'http://viaf.org/viaf/109557338/',
    'Pakenham, John': 'http://viaf.org/viaf/40930958/',
    'Bredin, Hugh': 'http://viaf.org/viaf/94376522',   # seems likely (lecturer at Queen's Univ. Belfast)
    'Buller, Norman': 'http://viaf.org/viaf/29058137',
    'McEldowney, Eugene': 'http://viaf.org/viaf/18143404',
    'Longley, Michael': 'http://viaf.org/viaf/39398205/',
    'Dugdale, Norman': 'http://viaf.org/viaf/50609413',
    'Simmons, James': 'http://viaf.org/viaf/92591927/',
    'Parker, Stewart': 'http://viaf.org/viaf/7497547/',
    'MacLaverty, Bernard': 'http://viaf.org/viaf/95151565',
    'Belfast Group': 'http://viaf.org/viaf/123393054/',
}

# URIs not found for:
#   Croskery, Lynette
#   Stronge, Marilyn
#   Foster, Rodney  (possibly the Jazz musician born 1939 N. Ireland [still no uri])
#   Ashton, Victor
#   Smyth, Paul
#   Robson, Bryan
#   Scott, Brian
#   Bull, Iris  (only one VIAF entry, doesn't seem like the right person)
#   Sullivan, Ronald
#   Brophy, Michael (possibly the one born in 1945, http://viaf.org/viaf/70921974 - http://trove.nla.gov.au/work/33952887?versionId=41792823)
#   Mitchell, Michael
#   Watton, Joan
#   Bond, John
#   Gallagher, Maurice
#   Harvey, W.J.
#   Johnston, J. K.


def generate_rdf(file):
    htmlfile = open(file)
    doc = BeautifulSoup(htmlfile)
    g = rdflib.Graph()
    # bind namespace prefixes for output
    g.bind('schema', SCHEMA_ORG)
    g.bind('bibo', BIBO)
    g.bind('dc', DC)

    # create a blank node for the archival collection at Queen's Belfast (no URI)
    coll = rdflib.BNode()
    for t in [ARCH.Collection, SCHEMA_ORG.CreativeWork, DCMITYPE.Collection]:
        g.add((coll, rdflib.RDF.type, t))
    g.add((coll, SCHEMA_ORG.name, rdflib.Literal(doc.body.h1.text)))
    g.add((coll, SCHEMA_ORG.description, rdflib.Literal(doc.body.find(id='about').text)))
    g.add((coll, SCHEMA_ORG.about, rdflib.URIRef(NAME_URIS['Belfast Group'])))
    # TODO: add information about owning archive ?
    # NOTE: PDF with collection listing is here:
    # http://www.qub.ac.uk/directorates/InformationServices/TheLibrary/FileStore/Filetoupload,312673,en.pdf
    # but that doesn't seem like a very good URI to reference
# queen's u belfast mentions some collections are in archives hub... doesn't seem to include this one
# possibly relevant? http://archiveshub.ac.uk/data/gb247-msgen874-875  (hobsbaum at glasgow)

    # NOTE: possibly just hard-code generating RDF for the description of Hobsbaum & the group
    # as presented in the description of the collection
# roughly this content
#     <rdf:Description rdf:about="http://viaf.org/91907300/">
#   <schema:name>Philip Hobsbaum</schema:name>
#   <rdf:type rdf:resource="http://schema.org/Person"/>
#   <schema:jobTitle xml:lang="en">Lecturer</schema:jobTitle>
#   <schema:affiliation rdf:resource="http://viaf.org/216613925/"/>
#   <schema:birthDate xml:lang="en">1932</schema:birthDate>
#   <schema:deathDate xml:lang="en">2005</schema:deathDate>
# </rdf:Description>

# <rdf:Description rdf:about="http://viaf.org/123393054/">
#   <schema:name>the Belfast Creative Writing Group</schema:name>
#   <schema:name>"The Group"</schema:name>
#   <schema:founder rdf:resource="http://viaf.org/91907300/"/>
#   <schema:member rdf:resource="http://viaf.org/viaf/92591927/"/>
#   <schema:member rdf:resource="http://viaf.org/viaf/7497547/"/>
#   <schema:member rdf:resource="http://viaf.org/viaf/39398205/"/>
#   <schema:member rdf:resource="http://viaf.org/viaf/109557338/"/>
#   <!-- todo: bernard mcclaverty -->
# </rdf:Description>

    for div in doc.find_all('div'):
        # only include typescript content (should be all but one)
        if 'Typescript' not in div.text:
            continue

        # create a blank node for the manuscript object
        msnode = rdflib.BNode()
        g.add((coll, SCHEMA_ORG.mentions, msnode))
        g.add((msnode, rdflib.RDF.type, BIBO.Manuscript))

        content = list(div.stripped_strings)
        first_line = content[0]
        # first line should start with the author's name (if known)
        # FIXME: a few have multiple authors
        name_match = NAME_REGEX.match(first_line)
        if name_match:
            last_name = name_match.group('last').strip()
            first_name = name_match.group('first').strip()
            name_key = '%s, %s' % (last_name, first_name)
            full_name = '%s %s' % (first_name, last_name)

            # use known URI if possible
            if name_key in NAME_URIS:
                author = rdflib.URIRef(NAME_URIS[name_key])
            else:
                author = rdflib.BNode()

            # relate person to manuscript as author, include name information
            g.add((msnode, SCHEMA_ORG.author, author))
            g.add((author, rdflib.RDF.type, SCHEMA_ORG.Person))
            g.add((author, SCHEMA_ORG.name, rdflib.Literal(full_name) ))
            g.add((author, SCHEMA_ORG.familyName, rdflib.Literal(last_name) ))
            g.add((author, SCHEMA_ORG.givenName, rdflib.Literal(first_name) ))


        # A *few* items include a date; add it to the RDF when present
        last_line = content[-1]
        if 'Undated' not in last_line:
            date_match = DATE_REGEX.match(last_line)
            date = None
            if date_match:
                date = '%s-%s-%s' % (date_match.group('year'),
                                     date_match.group('month'),
                                     date_match.group('day'))
            else:
                year_match = YEAR_REGEX.match(last_line)
                if year_match:
                    date = year_match.group('year')

            if date is not None:
                # NOTE: using dc:date since it's not clear what date this would be
                # (not necessarily a publication/creation date, e.g. one of the more specific schema.org)
                g.add((msnode, DC.date, rdflib.Literal(date)))

        # collection desription includes notes about poetry, short story, etc.
        # including as genre to avoid losing information
        if 'poem' in first_line.lower():
            g.add((msnode, SCHEMA_ORG.genre, rdflib.Literal('poetry')))
        elif 'short story' in div.text.lower() or 'short stories' in div.text.lower():
            g.add((msnode, SCHEMA_ORG.genre, rdflib.Literal('short story')))
        # one case is a book chapter...
        # some marked as possible translations?

        # collection description includes number of pages for each; go ahead and include
        pages = PAGES_REGEX.search(div.text)
        if pages:
            g.add((msnode, BIBO.numPages, rdflib.Literal(pages.group('num'))))

        titles = []
        for italic_text in div.find_all('i'):
            for title in italic_text.stripped_strings:
                titles.append(title)

        # if only one title, no parts
        if len(titles) == 1:
            title = rdflib.Literal(titles[0])
            g.add((msnode, SCHEMA_ORG.name, title))
        # multiple titles; use document parts to describe
        else:
            for title in titles:
                docpart = rdflib.BNode()
                # this item is a document part with a title, related to ms by dc:hasPart
                g.add((docpart, rdflib.RDF.type, BIBO.DocumentPart))
                g.add((docpart, SCHEMA_ORG.name, rdflib.Literal(title)))
                g.add((docpart, DC.title, rdflib.Literal(title)))
                g.add((msnode, DC.hasPart, docpart))


    # use input filename as base, but generate as .xml in current directory
    basename, ext = os.path.splitext(os.path.basename(file))
    filename = '%s.xml' % basename
    print 'Saving as %s' % filename
    with open(filename, 'w') as datafile:
        g.serialize(datafile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate RDF from Queens University Belfast Group description')
    parser.add_argument('file', metavar='FILE',
                        help='HTML file to be parsed for generating RDF')
    args = parser.parse_args()
    generate_rdf(args.file)
