# -*- coding: utf-8 -*-
"""
Implement graph products

G graph is the undirected base graph

>>> G = nx.Graph()

H graph is the "pop design" graph

Each node u in the graph G has a property "H" which specifies the H graph to use

>>> G.add_nodes_from([ ('a', dict(H='style_a')), ('b', dict(H='style_b')), ('c', dict(H='style_c'))])

The 'H' attribute of a node in G refers to the key in the 'H_graphs' dictionary:

>>> H_graphs = {}
>>> H_graphs['style_a'] = nx.trivial_graph()
>>> H_graphs['style_b'] = nx.cycle_graph(2)
>>> H_graphs['style_c'] = nx.cycle_graph(3)

Edges in the graph G specify edges between pops, and have an operator which specifies the interconnection method (covered below). 

Valid operators are cartesian, rooted, strong, or tensor.

>>> G.add_edges_from([('a','b', dict(operator = 'cartesian')), ('a','c', dict(operator = 'rooted')),  ('b','c', dict(operator = 'tensor'))])

Nodes in output graph are the tuple (u,v) for u in G for v in G[u]['H']

>>> sorted(node_list(G, H_graphs))
[('a', 0), ('b', 0), ('b', 1), ('c', 0), ('c', 1), ('c', 2)]

Intra PoP links are from the relevant H graph

>>> sorted(intra_pop_links(G, H_graphs))
[(('b', 0), ('b', 1)), (('c', 0), ('c', 1)), (('c', 0), ('c', 2)), (('c', 1), ('c', 2))]

>>> sorted(inter_pop_links(G, H_graphs))


"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen, Eric Parsonage

import networkx as nx
import logging
import itertools

LOG = logging.getLogger("ANK")

__all__ = ['graph_product']

def graph_product():
    pass

def node_list(G, H_graphs):
    # TODO: work out how to retain node properties
    return [ (u,v) for u in G for v in H_graphs[G.node[u]['H']] ]

def intra_pop_links(G, H_graphs):
    return [ ((u,v1), (u,v2)) for u in G for (v1, v2) in H_graphs[G.node[u]['H']].edges() ]

def inter_pop_links(G, H_graphs):
    #TODO:: list any edges without operator marked on them
    edges = []
    cartesian_operators = set(["cartesian", "strong"])
    tensor_operators = set(["tensor", "strong"])
    for (u1, u2) in G.edges():
        operator = G[u1][u2]['operator']
        H1 = H_graphs[G.node[u1]['H']]
        H2 = H_graphs[G.node[u2]['H']]
        if operator in cartesian_operators:
            edges += [((u1, v1), (u2, v2)) for v1 in H1 for v2 in H2 if v1 == v2]
        if operator in tensor_operators:
            edges += [((u1, v1), (u2, v2)) for v1 in H1 for v2 in H2
                    if ( (v1, v2) in H1.edges() or (v1,v2) in H2.edges())]
        if operator in tensor_operators:
            edges += [((u1, v1), (u2, v2)) for v1 in H1 for v2 in H2
                    if H1.node[v1].get("root") == H2.node[v2].get("root") == True ]

    return edges
