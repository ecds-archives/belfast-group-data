#!/usr/bin/env python

import argparse
import glob
import json
import networkx as nx
from networkx.readwrite import gexf
import rdflib
from rdflib.collection import Collection as RdfCollection

# simple script to load rdf data and convert into a networkx graph,
# then exported as GEXF for manual interaction with tools like Gephi


SCHEMA_ORG = rdflib.Namespace('http://schema.org/')
DC = rdflib.Namespace('http://purl.org/dc/terms/')


class Rdf2Gexf(object):

    def __init__(self, files, outfile):
        self.outfile = outfile

        self.graph = rdflib.Graph()
        for infile in files:
            self.graph.parse(infile)
        print '%d triples in %d files' % (len(self.graph), len(files))

        self.network = nx.MultiDiGraph()

        # iterate through rdf triples and add to the graph
        for triple in self.graph:
            subj, pred, obj = triple

            if pred == rdflib.RDF.first or pred == rdflib.RDF.rest:
                continue
            # FIXME: iterating through all triples results in
            # rdf sequences (first/rest) being handled weirdly...

            # make sure subject and object are added to the graph as nodes,
            # if appropriate
            self._add_nodes(triple)

            # get the short-hand name for property or edge label
            name = self._edge_label(pred)

            # if the object is a literal, add it to the node as a property of the subject
            if subj in self.network and isinstance(obj, rdflib.Literal) \
               or pred == rdflib.RDF.type:
                if pred == rdflib.RDF.type:
                    ns, val = rdflib.namespace.split_uri(obj)
                    # special case (for now)
                    if val == 'Manuscript':
                        if isinstance(self.graph.value(subj, DC.title), rdflib.BNode):
                            val = 'BelfastGroupSheet'

                else:
                    val = unicode(obj)
                self.network.node[subj][name] = val

            # otherwise, add an edge between the two resource nodes
            else:
                self.network.add_edge(subj, obj, label=name)

        print '%d nodes, %d edges' % (self.network.number_of_nodes(),
                                      self.network.number_of_edges())
        gexf.write_gexf(self.network, self.outfile)

    def _node_label(self, res):
        # NOTE: consider adding/calculating a preferredlabel
        # for important nodes in our data
        title = self.graph.value(res, DC.title)
        if title:
            # if title is a bnode, convert from list/collection
            if isinstance(title, rdflib.BNode):
                title_list = RdfCollection(self.graph, title)
                title = 'group sheet: ' + '; '.join(title_list)
                # truncate list if too long
                if len(title) > 50:
                    title = title[:50] + ' ...'

            # otherwise, title should be a literal (no conversion needed)

            return title

        name = self.graph.value(res, SCHEMA_ORG.name)
        if name:
            return name

        # as a fall-back, use type for a label
        type = self.graph.value(res, rdflib.RDF.type)
        if type:
            ns, short_type = rdflib.namespace.split_uri(type)
            return short_type

    def _edge_label(self, pred):
        # get the short-hand name for property or edge label
        ns, name = rdflib.namespace.split_uri(pred)
        return name

    def _add_nodes(self, triple):
        subj, pred, obj = triple

        if self._include_as_node(subj) and subj not in self.network:
            self._add_node(subj)

        # special case: don't treat title list as a node in the network
        if pred == DC.title and isinstance(obj, rdflib.BNode):
            return

        if pred != rdflib.RDF.type and self._include_as_node(obj) \
           and obj not in self.network:
            self._add_node(obj)

    def _include_as_node(self, res):
        # determine if a URI should be included in the network graph
        # as a node
        if isinstance(res, rdflib.URIRef) or isinstance(res, rdflib.BNode):
            return True

    def _add_node(self, res):
        # add an rdf term to the network as a node
        attrs = {}
        label = self._node_label(res)
        if label is not None:
            attrs['label'] = label
        self.network.add_node(res, **attrs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate a network graph file in GEXF format based on RDF'
    )
    parser.add_argument('files', metavar='FILE', nargs='+',
                        help='files to be processed')
    parser.add_argument('-o', '--output', metavar='OUTFILE',
                        help='filename for GEXF to be generated',
                        required=True)
    args = parser.parse_args()
    Rdf2Gexf(args.files, args.output)
