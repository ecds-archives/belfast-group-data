#!/usr/bin/env python

from setuptools import setup, find_packages
import belfastdata

LONG_DESCRIPTION = None
try:
    # read the description if it's there
    with open('README.rst') as desc_f:
        LONG_DESCRIPTION = desc_f.read()
except:
    pass

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: End Users/Desktop',  # scripts
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Utilities',
]

setup(
    name='belfastdata',
    version=belfastdata.__version__,
    author='Emory University Libraries',
    author_email='libsysdev-l@listserv.cc.emory.edu',
    url='https://github.com/emory-libraries-disc/belfast-group-data',
    license='Apache License, Version 2.0',
    packages=find_packages(),

    install_requires=[
        'rdflib>=3.0',
        'requests>=1.1',
        'BeautifulSoup4',
        'progressbar',  # make optional?
        'Django',
        'networkx',
        'SPARQLWrapper',
    ],

    # # indexdata utils are optional. They include things like PDF text stripping (pyPdf).
    # # Be sure to include the below in your own pip dependencies file if you need to use
    # # the built in indexer utility support.
    # extras_require={
    #     'indexdata_util': ['pyPdf', ],
    # },

    description='Utilities to harvest and process RDF data relating to the Belfast Group',
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
    scripts=['scripts/harvest-rdf', 'scripts/harvest-related',
             'scripts/queens_belfast_rdf', 'scripts/smush-groupsheets',
             'gscripts/rdf2gexf',
             'scripts/belfast_dataset'],
)
