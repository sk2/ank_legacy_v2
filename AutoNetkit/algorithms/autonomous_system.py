# -*- coding: utf-8 -*-
"""
Autonomous System functions
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen

__all__ = ['nodes_by_as', 'get_as_graphs', 'igp_graph', 
        'as_graph_dict', 'get_as_list']

import networkx as nx
from collections import defaultdict

#TODO: cut the number of functions presented here, many can be built from
# other functions

def nodes_by_as(network):
    """ returns dict of nodes indexed by AS """
#TODO: use itertools and groupby here
    as_dict = defaultdict(list)
    for node in network.graph:
        asn = network.asn(node)
        if asn is None:
            continue
        as_dict[asn].append(node)
    return as_dict

def get_as_list(network):    
    """Returns each AS ID in network."""        
    #returns list of unique as numbers 
    return set( network.asn(n) for n in network.graph )

def igp_graph(network):
    """Returns IGP graph for network - based on physical graph with inter-AS links removed"""
    G = network.graph.subgraph(network.graph.nodes())
# Remove inter-AS links
    edges_to_remove = ( (s,t) for (s,t) in G.edges()
            if network.asn(s) != network.asn(t))
    G.remove_edges_from(edges_to_remove)
    return G

def as_graph_dict(network):
    """as graphs indexed by asn
#TODO: use this in ip allocs"""
    return dict( (as_graph.asn, as_graph) for as_graph in get_as_graphs(network))
    
def get_as_graphs(network):   
    """Returns a graph for each AS."""
    as_graphs = []
    #for asn, nodes in as_dict.items():
    for asn, nodes in network.groupby('asn'):
        # Create seperate graph otherwise all have same attributes
        """
        The graph, edge or node attributes just point to the original graph. 
        So changes to the node or edge structure will not be reflected in the
        original graph while changes to the attributes will.
        To create a subgraph with its own copy of the edge/node attributes use:
            nx.Graph(G.subgraph(nbunch))
        """
        if network.graph.is_directed():
            as_graph = nx.DiGraph(network.graph.subgraph(nodes))
        else:
            as_graph = nx.Graph(network.graph.subgraph(nodes))
        as_graph.name = as_graph.asn = int(asn)
        as_graphs.append(as_graph)
    return as_graphs

