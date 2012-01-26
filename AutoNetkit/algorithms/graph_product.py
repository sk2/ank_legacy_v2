# -*- coding: utf-8 -*-
"""
Implementation of graph products

Introduction
==============

>>> G_out = graph_product("../lib/examples/topologies/gptest.graphml")

Implementation
==============

Disable plotting of examples in doctests:
>>> plot = lambda x,y: None

Note: add_nodes_from will update the property of a node if it already exists
TODO: add example of this

G graph is the undirected base graph

>>> G = nx.Graph()

H graph is the "pop design" graph

Each node u in the graph G has a attribute "H" which specifies the H graph to use

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

Combined
-----------
Intra and Inter pop links can be combined:

>>> G['a']['b']['operator'] = 'cartesian'
>>> edge_list = intra_pop_links(G, H_graphs) + inter_pop_links(G, H_graphs)
>>> plot(nx.Graph(edge_list), "combined")

.. figure::  ../../images/graph_products/combined.*

Attributes
===========

The above code generates the list of nodes and the list of edges in the new graph. They do not contain attributes.
The node and edge attributes are copied from the relevant G and H graphs using the rules defined in the following sections.

Node Attributes
=========================
Nodes in AutoNetkit can have attributes. A number of attributes carry special meaning, such as *pop* and *asn*, but the user is free to add their own attributes.
These attributes are preserved from the G and H graphs.

For attributes that exist in both the H graph and the G graph, the attribute in the H graph is used. This is the idea of inheritance - the H graph is more specific.

Attributes associated with the graph products, such as *H* and *root* are not propagated to the output graph, as they are used in the generation process, but are not relevant to AutoNetkit. If the user wishes for a specific attribute to be in the output graph, they should add that to the relevant node.

Example
---------

Add some extra attributes to the G graph defined above:

>>> G.add_nodes_from([ ('a', dict(color='red')), ('b', dict(color='blue'))])
>>> G.nodes(data=True)
[('a', {'color': 'red', 'H': 'style_d'}), ('b', {'color': 'blue', 'H': 'style_d'})]
>>> propagate_node_attributes(G, H_graphs, node_list(G, H_graphs))
[(('a', 0), {'color': 'red'}), (('a', 1), {'color': 'red'}), (('a', 2), {'color': 'red'}), (('b', 0), {'color': 'blue'}), (('b', 1), {'color': 'blue'}), (('b', 2), {'color': 'blue'})]

>>> G.add_nodes_from([ ('a', dict(color='red', H='style_e')), ('b', dict(color='blue', H='style_e'))])
>>> G.nodes(data=True)
[('a', {'color': 'red', 'H': 'style_e'}), ('b', {'color': 'blue', 'H': 'style_e'})]

Define a new H graph with some attributes. This shows the *color* attribute from the H graph over-writing that of the G graph. It can be seen that node ('a', 1) and ('b', 1) both have the color *green* from the H graph.

>>> H_graphs['style_e'] = H_graphs['style_d'].copy()
>>> H_graphs['style_e'].add_nodes_from( [(1, dict(color='green'))])
>>> H_graphs['style_e'].nodes(data=True)
[(0, {'root': True}), (1, {'color': 'green'}), (2, {})]

>>> propagate_node_attributes(G, H_graphs, node_list(G, H_graphs))
[(('a', 0), {'color': 'red'}), (('a', 1), {'color': 'green'}), (('a', 2), {'color': 'red'}), (('b', 0), {'color': 'blue'}), (('b', 1), {'color': 'green'}), (('b', 2), {'color': 'blue'})]

Edge Attributes
=========================
Edge attributes are simpler. Inter-Pop links obtain their data from the G graph.
Intra-Pop links obtain their data from their H graph.

Example
--------
For clarity, use the cartesian operator:

>>> G['a']['b']['operator'] = 'cartesian'

Add a new attribute to the edge in the G graph:

>>> G.add_edges_from( [('a', 'b', dict(speed=10))])
>>> G.edges(data=True)
[('a', 'b', {'operator': 'cartesian', 'speed': 10})]
>>> edge_list = intra_pop_links(G, H_graphs) + inter_pop_links(G, H_graphs)

>>> H_graphs['style_f'] = H_graphs['style_d'].copy()
>>> H_graphs['style_f'].add_edges_from([ (0, 1, dict(speed=100)), (1, 2, dict(speed=150))])
>>> H_graphs['style_f'].edges(data=True)
[(0, 1, {'speed': 100}), (1, 2, {'speed': 150})]

And use the new H style:

>>> G.add_nodes_from([ ('a', dict(H='style_f')), ('b', dict(H='style_f'))])
>>> propagate_edge_attributes(G, H_graphs, edge_list)
[(('a', 0), ('a', 1), {'speed': 100}), (('a', 1), ('a', 2), {'speed': 150}), (('b', 0), ('b', 1), {'speed': 100}), (('b', 1), ('b', 2), {'speed': 150}), (('a', 0), ('b', 0), {'speed': 10}), (('a', 1), ('b', 1), {'speed': 10}), (('a', 2), ('b', 2), {'speed': 10})]
>>> plot(nx.Graph(propagate_edge_attributes(G, H_graphs, edge_list)), "edge_attributes")

.. figure::  ../../images/graph_products/edge_attributes.*

"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen, Eric Parsonage

import networkx as nx
import logging
import itertools
import os
import pprint
import math
from collections import defaultdict

LOG = logging.getLogger("ANK")

__all__ = ['graph_product']

def remove_yed_edge_id(G):
    for s, t, data in G.edges(data=True):
        try:
            del G[s][t]['id']
        except KeyError:
            continue
    return G

def remove_gml_node_id(G):
    for n in G:
        try:
            del G.node[n]['id']
        except KeyError:
            continue
    return G

def graph_product(G_file):
    
    #TODO: take in a graph (eg when called from graphml) rather than re-reading the graph again
    LOG.info("Applying graph product to %s" % G_file)
    H_graphs = {}
    try:
        G = nx.read_graphml(G_file).to_undirected()
    except IOError:
        G = nx.read_gml(G_file).to_undirected()
        return
    G = remove_yed_edge_id(G)
    G = remove_gml_node_id(G)
#Note: copy=True causes problems if relabelling with same node name -> loses node data
    G = nx.relabel_nodes(G, dict((n, data.get('label', n)) for n, data in G.nodes(data=True)))
    G_path = os.path.split(G_file)[0]
    H_labels  = defaultdict(list)
    for n, data in G.nodes(data=True):
        H_labels[data.get("H")].append(n)

    for label in H_labels.keys():
        try:
            H_file = os.path.join(G_path, "%s.graphml" % label)
            H = nx.read_graphml(H_file).to_undirected()
        except IOError:
            try:
                H_file = os.path.join(G_path, "%s.gml" % label)
                H = nx.read_gml(H_file).to_undirected()
            except IOError:
                LOG.warn("Unable to read H_graph %s, used on nodes %s" % (H_file, ", ".join(H_labels[label])))
                return
        root_nodes = [n for n in H if H.node[n].get("root")]
        if len(root_nodes):
# some nodes have root set
            non_root_nodes = set(H.nodes()) - set(root_nodes)
            H.add_nodes_from( (n, dict(root=False)) for n in non_root_nodes)
        H = remove_yed_edge_id(H)
        H = remove_gml_node_id(H)
        nx.relabel_nodes(H, dict((n, data.get('label', n)) for n, data in H.nodes(data=True)), copy=False)
        H_graphs[label] = H

    G_out = nx.Graph()
    G_out.add_nodes_from(node_list(G, H_graphs))
    G_out.add_nodes_from(propagate_node_attributes(G, H_graphs, G_out.nodes()))
    G_out.add_edges_from(intra_pop_links(G, H_graphs))
    G_out.add_edges_from(inter_pop_links(G, H_graphs))
    G_out.add_edges_from(propagate_edge_attributes(G, H_graphs, G_out.edges()))
#TODO: need to set default ASN, etc?
    return G_out

def node_list(G, H_graphs):
    # TODO: work out how to retain node attributes
    return [ (u,v) for u in G for v in H_graphs[G.node[u]['H']] ]

def intra_pop_links(G, H_graphs):
    return [ ((u,v1), (u,v2)) for u in G for (v1, v2) in H_graphs[G.node[u]['H']].edges() ]

def inter_pop_links(G, H_graphs, default_operator='cartesian'):
    #TODO:: list any edges without operator marked on them
    edges = []
    cartesian_operators = set(["cartesian", "strong"])
    tensor_operators = set(["tensor", "strong"])
    for (u1, u2) in G.edges():
        try:
            operator = G[u1][u2]['operator']
        except KeyError:
            operator =  default_operator
        H1 = H_graphs[G.node[u1]['H']]
        H2 = H_graphs[G.node[u2]['H']]
# Node lists - if 'root' set then only use root nodes
        try:
            N1 = [n for n in H1 if H1.node[n]['root']]
        except KeyError:
            N1 = [n for n in H1]
        try:
            N2 = [n for n in H2 if H2.node[n]['root']]
        except KeyError:
            N2 = [n for n in H2]
        
        LOG.debug("Adding edges for (%s,%s) with operator %s" % (u1, u2, operator))

        LOG.debug("H nodes for u1 %s: %s" % ( G.node[u1]['H'], ", ".join(N1)))
        LOG.debug("H nodes for u2 %s: %s" % ( G.node[u2]['H'], ", ".join(N2)))
# 'root' not set
#TODO: fold rooted back into special case of cartesian - just do the same for now
        if operator == 'rooted':
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2
                    if H1.node[v1].get("root") == H2.node[v2].get("root") == True ]
            LOG.debug("Rooted product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges

        if operator == 'lexical':
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2]
            LOG.debug("Lexical product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges

        if operator in cartesian_operators:
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2 if v1 == v2]
            LOG.debug("Cartesian product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges
        if operator in tensor_operators:
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2
                    if  H1.has_edge(v1, v2) or H2.has_edge(v1,v2)]
            LOG.debug("Tensor product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges

    return edges


def propagate_node_attributes(G, H_graphs, node_list):
    retval = []
    for (u,v) in node_list:
        u_v_data = dict(G.node[u])
        v_data = dict(H_graphs[u_v_data['H']].node[v])
        u_v_data.update(v_data)
        try:
# append to current label to ensure unique
            if u_v_data['label'] != v:
                u_v_data['label'] = "%s%s_%s" % (u, v, u_v_data['label'])
            else:
                u_v_data['label'] = "%s%s" % (u, v)
        except KeyError:
            u_v_data['label'] = "%s%s" % (u, v)

# set pop to be u, used in ibgp, dns, etc as the layer 2 group
        u_v_data['pop'] = u
        try:
            u_x = float(G.node[u]['x_pos'])
            u_y = float(G.node[u]['y_pos'])
        except KeyError:
# Manually configure positions
            G_nodes = sorted(G.nodes())
            grid_size = int(math.ceil(math.sqrt(len(G_nodes))))
            scaling =3
            co_ords = [ (x*scaling, y*scaling) for x in range(grid_size) for y in range(grid_size)]
            G_index = G_nodes.index(u)
            (u_x, u_y) = co_ords[G_index]

# Now need to map index of v in H to a grid
        H_nodes = sorted(H_graphs[u_v_data['H']].nodes())
        grid_size = int(math.ceil(math.sqrt(len(H_nodes))))
        co_ords = [ (x,y) for x in range(grid_size) for y in range(grid_size)]
        H_index = H_nodes.index(v)
        scaling = 100
        (v_x, v_y) = co_ords[H_index]
        u_v_data['x_pos'] = (u_x + v_x) * scaling
        u_v_data['y_pos'] = (u_y + v_y) * scaling


# Remove H and root (if set) which was used in graph construction - no need to send to AutoNetkit
        del u_v_data['H']
        try:
            del u_v_data['root']
        except KeyError:
            pass
        retval.append( ((u, v), u_v_data))
    return retval

def propagate_edge_attributes(G, H_graphs, edge_list):
    retval = []
    for s, t in edge_list:
        (u1, v1) = s
        (u2, v2) = t
        if u1 == u2:
# intra-pop
            edge_data = H_graphs[G.node[u2]['H']].get_edge_data(v1, v2)
        else:
# inter-pop
#TODO: why do we need {}?
            edge_data = G.get_edge_data(u1, u2)
            try:
                del edge_data['operator']
            except KeyError:
                pass

        retval.append( (s, t, edge_data))
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
# check each element is in graph
            if len(pos) != len(G):
# use spring layout, as different to built in graph examples
                pos = nx.spring_layout(G)
        except (IndexError, TypeError):
# Use spring layout - can't do in a row or won't show cycles (due to overlap)
                pos = nx.spring_layout(G)

        nx.draw(G, pos, node_color='#A0CBE2', node_size=500, width=1)

        edge_labels = {}
        for s, t, data in G.edges(data=True):
            if len(data):
                data = ", ".join( "%s: %s" % (key, val) for (key, val) in data.items())
                edge_labels[(s,t)] = data

        nx.draw_networkx_edge_labels(G, pos, edge_labels =edge_labels)
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


