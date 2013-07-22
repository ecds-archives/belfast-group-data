Belfast Group data
==================

RDF data about the Belfast Group, its members, and associated persons.

Developed as part of the `Digital Scholarship Commons`_ project `Networking the Belfast Group`_.

.. _Digital Scholarship Commons: http://disc.library.emory.edu/
.. _Networking the Belfast Group: http://web.library.emory.edu/disc/projects/networking-belfast-group


0.1
---

Initial release includes preliminary test data and scripts for harvesting
and preparing the data for use, including some consolidation and 'smushing'
work, as well as adding some inferences based on connections that are
implicit in the data.  Also includes a GEXF file containing a network graph
based on a subset of the harvested data, for use with tools such as Gephi.


Usage
-----

To run the scripts in a checked out copy of this repository, install
dependencies by running ``pip install .`` in the top-level directory.
To harvest RDF from VIAF, GeoNames.org, and DBpedia for entities
referenced in the dataset, run ``belfast_dataset -r``.
