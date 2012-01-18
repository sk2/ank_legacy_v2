# -*- coding: utf-8 -*-
"""
Implementation of graph products

Introduction
==============

Disable plotting of examples in doctests:
>>> plot = lambda x,y: None

G graph is the undirected base graph

>>> G = nx.Graph()

H graph is the "pop design" graph

Each node u in the graph G has a property "H" which specifies the H graph to use

>>> G.add_nodes_from([ ('a', dict(H='style_a')), ('b', dict(H='style_b')), ('c', dict(H='style_c'))])

The 'H' attribute of a node in G refers to the key in the 'H_graphs' dictionary:

>>> H_graphs = {}

>>> H_graphs['style_a'] = nx.trivial_graph()
>>> plot(H_graphs['style_a'], "style_a")

.. figure::  ../../images/graph_products/style_a.*

>>> H_graphs['style_b'] = nx.cycle_graph(2)
>>> plot(H_graphs['style_b'], "style_b")

.. figure::  ../../images/graph_products/style_b.*

>>> H_graphs['style_c'] = nx.cycle_graph(3)
>>> plot(H_graphs['style_c'], "style_c")

.. figure::  ../../images/graph_products/style_c.*

>>> H_graphs['style_d'] = nx.Graph( [(0,1), (1,2)])
>>> H_graphs['style_d'].add_nodes_from( [(0, dict(root=True))])
>>> plot(H_graphs['style_d'], "style_d")

.. figure::  ../../images/graph_products/style_d.*

Edges in the graph G specify edges between pops, and have an operator which specifies the interconnection method (covered below). 

Valid operators are cartesian, rooted, strong, or tensor.

>>> G.add_edges_from([('a','b', dict(operator = 'cartesian')), ('a','c', dict(operator = 'rooted')),  ('b','c', dict(operator = 'tensor'))])

Nodes in output graph are the tuple (u,v) for u in G for v in G[u]['H']

>>> sorted(node_list(G, H_graphs))
[('a', 0), ('b', 0), ('b', 1), ('c', 0), ('c', 1), ('c', 2)]


Examples
===========

Using smaller case study for the following examples:

>>> G.clear()
>>> G.add_nodes_from([ ('a', dict(H='style_d')), ('b', dict(H='style_d'))])
>>> G.add_edge( 'a', 'b')

>>> plot(G, "G")

.. figure::  ../../images/graph_products/G.*


Intra-PoP links
=========================

Intra PoP links are from the relevant H graph:

>>> sorted(intra_pop_links(G, H_graphs))
[(('a', 0), ('a', 1)), (('a', 1), ('a', 2)), (('b', 0), ('b', 1)), (('b', 1), ('b', 2))]

>>> plot(nx.Graph(intra_pop_links(G, H_graphs)), "intra_pop_links")

.. figure::  ../../images/graph_products/intra_pop_links.*


Inter-PoP links
=========================

Cartesian Product
------------------

>>> G['a']['b']['operator'] = 'cartesian'
>>> inter_pop_links(G, H_graphs)
[(('a', 0), ('b', 0)), (('a', 1), ('b', 1)), (('a', 2), ('b', 2))]

>>> plot(nx.Graph(inter_pop_links(G, H_graphs)), "cartesian")

.. figure::  ../../images/graph_products/cartesian.*

Rooted Product
------------------

>>> G['a']['b']['operator'] = 'rooted'
>>> inter_pop_links(G, H_graphs)
[(('a', 0), ('b', 0))]
>>> plot(nx.Graph(inter_pop_links(G, H_graphs)), "rooted")

.. figure::  ../../images/graph_products/rooted.*

Lexical Product
------------------

>>> G['a']['b']['operator'] = 'lexical'
>>> inter_pop_links(G, H_graphs)
[(('a', 0), ('b', 0)), (('a', 0), ('b', 1)), (('a', 0), ('b', 2)), (('a', 1), ('b', 0)), (('a', 1), ('b', 1)), (('a', 1), ('b', 2)), (('a', 2), ('b', 0)), (('a', 2), ('b', 1)), (('a', 2), ('b', 2))]

>>> plot(nx.Graph(inter_pop_links(G, H_graphs)), "lexical")

.. figure::  ../../images/graph_products/lexical.*

Tensor Product
------------------

>>> G['a']['b']['operator'] = 'tensor'
>>> inter_pop_links(G, H_graphs)
[(('a', 0), ('b', 1)), (('a', 1), ('b', 0)), (('a', 1), ('b', 2)), (('a', 2), ('b', 1))]
>>> plot(nx.Graph(inter_pop_links(G, H_graphs)), "tensor")

.. figure::  ../../images/graph_products/tensor.*

Strong Product
------------------

>>> G['a']['b']['operator'] = 'strong'
>>> inter_pop_links(G, H_graphs)
[(('a', 0), ('b', 0)), (('a', 1), ('b', 1)), (('a', 2), ('b', 2)), (('a', 0), ('b', 1)), (('a', 1), ('b', 0)), (('a', 1), ('b', 2)), (('a', 2), ('b', 1))]

>>> plot(nx.Graph(inter_pop_links(G, H_graphs)), "strong")

.. figure::  ../../images/graph_products/strong.*


Node Attributes
=========================
Nodes in AutoNetkit can have attributes. A number of attributes carry special meaning, such as *pop* and *asn*, but the user is free to add their own attributes.
These attributes are preserved from the G and H graphs.



Add some extra properties to the G graph defined above:

>>> G.add_nodes_from([ ('a', dict(color='red')), ('b', dict(color='blue'))])
>>> G.nodes(data=True)
[('a', {'color': 'red', 'H': 'style_d'}), ('b', {'color': 'blue', 'H': 'style_d'})]
>>> propagate_node_attributes(G, H_graphs, node_list(G, H_graphs))
[('a', 0, {'color': 'red'}), ('a', 1, {'color': 'red'}), ('a', 2, {'color': 'red'}), ('b', 0, {'color': 'blue'}), ('b', 1, {'color': 'blue'}), ('b', 2, {'color': 'blue'})]


>>> G.add_nodes_from([ ('a', dict(color='red', H='style_e')), ('b', dict(color='blue', H='style_e'))])
>>> G.nodes(data=True)
[('a', {'color': 'red', 'H': 'style_e'}), ('b', {'color': 'blue', 'H': 'style_e'})]


Define a new H graph with some properties:
>>> H_graphs['style_e'] = H_graphs['style_d'].copy()
>>> H_graphs['style_e'].add_nodes_from( [(1, dict(color='green'))])
>>> H_graphs['style_e'].nodes(data=True)
[(0, {'root': True}), (1, {'color': 'green'}), (2, {})]
>>> propagate_node_attributes(G, H_graphs, node_list(G, H_graphs))
[('a', 0, {'color': 'red'}), ('a', 1, {'color': 'green'}), ('a', 2, {'color': 'red'}), ('b', 0, {'color': 'blue'}), ('b', 1, {'color': 'green'}), ('b', 2, {'color': 'blue'})]


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
        if operator == 'rooted':
            edges += [((u1, v1), (u2, v2)) for v1 in H1 for v2 in H2
                    if H1.node[v1].get("root") == H2.node[v2].get("root") == True ]

        if operator == 'lexical':
            edges += [((u1, v1), (u2, v2)) for v1 in H1 for v2 in H2]

        if operator in cartesian_operators:
            edges += [((u1, v1), (u2, v2)) for v1 in H1 for v2 in H2 if v1 == v2]
        if operator in tensor_operators:
            edges += [((u1, v1), (u2, v2)) for v1 in H1 for v2 in H2
                    if  H1.has_edge(v1, v2) or H2.has_edge(v1,v2)]

    return edges


def propagate_node_attributes(G, H_graphs, node_list):
    retval = []
    for (u,v) in node_list:
        u_v_data = dict(G.node[u])
        v_data = dict(H_graphs[u_v_data['H']].node[v])
        u_v_data.update(v_data)
# Remove "root" which was used in graph construction - no need to send to AutoNetkit
        try:
            del u_v_data['H']
            del u_v_data['root']
        except KeyError:
            pass
        retval.append( (u, v, u_v_data))
    return retval

def plot(G, label="plot"):
    try:
        import matplotlib.pyplot as plt
        plt.clf()
# positions for examples
        try:
            labels = dict( (n, "%s%s" % (n[0], n[1])) for n in G)
            nx.relabel_nodes(G, labels, copy=False)
            pos = {
                    ('a0'): (0,2),
                    ('a1'): (0,1),
                    ('a2'): (0,0),
                    ('b0'): (1,2),
                    ('b1'): (1,1),
                    ('b2'): (1,0),
                    }
        except (IndexError, TypeError):
# Use spring layout - can't do in a row or won't show cycles (due to overlap)
                pos = nx.spring_layout(G)

        nx.draw(G, pos, node_color='#A0CBE2', node_size=500, width=1)
        fig = plt.gcf()
        fig.set_size_inches(4,4)
        plt.savefig("%s.pdf" % label)
        plt.savefig("%s.png" % label, dpi=72,
                bbox_inches='tight',
                pad_inches=0.1,
                )
    except ImportError:
# No matplotlib, don't fail the other tests due to this
        pass


