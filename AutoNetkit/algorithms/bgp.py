# -*- coding: utf-8 -*-
"""
BGP
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['ebgp_routers', 'get_ebgp_links', 'get_ebgp_graph',
           'ibgp_routers', 'get_ibgp_links', 'get_ibgp_graph',
           'initialise_bgp']

import itertools
import networkx as nx

def ebgp_edges(network):
    return ( (s,t) for s,t in network.g_session.edges()
            if network.asn(s) != network.asn(t))

def ibgp_edges(network):
    return ( (s,t) for s,t in network.g_session.edges()
            if network.asn(s) == network.asn(t))

def initialise_ebgp(network):
    """Adds edge for links that have router in different ASes

    """
    edges_to_add = ( (src, dst) for src, dst in network.graph.edges()
            if network.asn(src) != network.asn(dst))
    network.g_session.add_edges_from(edges_to_add)

def initialise_ibgp(network):
    edges_to_add = ( (s,t) for s in network.graph for t in network.graph 
            if (s is not t and
                network.asn(s) == network.asn(t)))
    network.g_session.add_edges_from(edges_to_add)

def initialise_bgp(network):
    initialise_ebgp(network)
    initialise_ibgp(network)

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

def ebgp_routers(network):
    """List of all routers with an eBGP link"""
    return list(set(item for pair in ebgp_edges(network) for item in pair))

def ibgp_routers(network):
    """List of all routers with an iBGP link"""
    # Note: this is the same as eBGP routers, but for a specific AS
    # routers in ibgp graph that have at least one edge
    # TODO: if get_ibgp_path design pattern changes, then this will need to
    # reflect the ibgp_graph
    return list(set(item for pair in ibgp_edges(network) for item in pair))

def get_ebgp_graph(network):
    """Returns graph of eBGP routers and links between them."""
    ebgp_graph = nx.DiGraph(network.g_session)
    ebgp_graph.name = 'ebgp'
    ebgp_graph.remove_edges_from( ibgp_edges(network))
#remove nodes that don't have an eBGP links
    non_ebgp_nodes =  [n for n in ebgp_graph if n not in ebgp_routers(network)]
    ebgp_graph.remove_nodes_from(non_ebgp_nodes)
    return ebgp_graph

    


def get_ibgp_graph(network):
    """Returns iBGP graph (full mesh currently) for an AS."""
    ibgp_graph = nx.DiGraph(network.g_session)
    ibgp_graph.name = 'ibgp'
    ibgp_graph.remove_edges_from( ebgp_edges(network))
    return ibgp_graph
