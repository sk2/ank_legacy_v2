# -*- coding: utf-8 -*-
"""
BGP
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['get_ebgp_routers', 'get_ebgp_links', 'get_ebgp_graph',
           'get_ibgp_routers', 'get_ibgp_links', 'get_ibgp_graph']

import itertools
import networkx as nx

#toDo: add docstrings
#TODO: remove "get" from name eg get_ebgp_graph -> ebgp_graph
def get_ebgp_links(network):
    #TODO: see if this is needed, or if just deal with eBGP graph
    """Returns links which are ebgp (between two different ases)"""
    return [e for e in get_ebgp_graph(network).edges()]

def get_ibgp_links(network):
    #TODO: see if this is needed, or if just deal with iBGP graph
    """Returns links which are ibgp
    (between two border routers in the same as)"""
    return [e for e in get_ibgp_graph(network).edges()]

def get_ebgp_routers(network):
    """Returns eBGP routers in network."""
    ebgp_routers = ( (s,t) for s,t in network.graph.edges()
            if network.asn(s) != network.asn(t))
    # Flatten into list of unique node names
    ebgp_routers = set(item for pair in ebgp_routers for item in pair)
    return list(ebgp_routers)

def get_ibgp_routers(network):
    """Returns iBGP routers in network."""
    # Note: this is the same as eBGP routers, but for a specific AS
    # routers in ibgp graph that have at least one edge
    # TODO: if get_ibgp_path design pattern changes, then this will need to
    # reflect the ibgp_graph
    return get_ibgp_graph(network).nodes()

def get_ebgp_graph(network):
    """Returns graph of eBGP routers and links between them."""
    ebgp_routers = get_ebgp_routers(network)
    ebgp_graph = network.graph.subgraph(ebgp_routers)
    # remove links between any two nodes in the same networ
    ebgp_graph.remove_edges_from( (s,t) for s,t in ebgp_graph.edges()
                                 if network.asn(s) == network.asn(t))
    ebgp_graph.name = "ebgp"
    return ebgp_graph

def get_ibgp_graph(network):
    """Returns iBGP graph (full mesh currently) for an AS."""
    #TODO: double check this
    #TODO: Use a Cisco/etc network design pattern algorithm for iBGP mesh
    ibgp_graph = nx.Graph(network.graph)
    # Remove edges, as iBGP design pattern will add edges
    ebgp_routers = set(get_ebgp_routers(network))
    ibgp_graph.remove_edges_from(e for e in ibgp_graph.edges())
    # Full mesh
    ibgp_graph.add_edges_from( (s,t) for s in ibgp_graph for t in ibgp_graph
                              if (s is not t and
                                  network.asn(s) == network.asn(t)))

    return ibgp_graph
