# -*- coding: utf-8 -*-
"""
Implement graph products

G graph is the undirected base graph

>>> G = nx.Graph()

H graph is the "pop design" graph

Each node u in the graph G has a property "H" which specifies the H graph to use

>>> G.add_nodes_from([ ('a', dict(H='style_a')), ('b', dict(H='style_b')), ('c', dict(H='style_b'))])

The 'H' attribute of a node in G refers to the key in the 'H_graphs' dictionary:

>>> H_graphs = {}
>>> H_graphs['style_a'] = nx.cycle_graph(1)
>>> H_graphs['style_b'] = nx.cycle_graph(2)

Edges in the graph G specify edges between pops, and have an operator which specifies the interconnection method (covered below). 

Valid operators are cartesian, rooted, strong, or tensor.

>>> G.add_edges_from([('a','b', dict(operator = 'cartesian')), ('a','c', dict(operator = 'cartesian')),  ('b','c', dict(operator = 'cartesian'))])

Nodes in output graph are the tuple (u,v) for u in G for v in G[u]['H']

>>> sorted(node_list(G, H_graphs))

Intra PoP links:




"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen, Eric Parsonage

import networkx as nx
import logging
import itertools

LOG = logging.getLogger("ANK")

__all__ = ['graph_product']


def node_list(G, H_graphs):
    # TODO: work out how to retain node properties
    retval = []
    for u in G:
        H_label = G.node[u]['H']
        H = H_graphs[H_label]
        retval += [(u,v) for v in H for u in G]

    return list(retval)

def graph_product(G, H_graphs):
    """

    """
    pass

