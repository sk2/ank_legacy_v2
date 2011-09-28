# -*- coding: utf-8 -*-
"""
BGP
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['ebgp_routers', 'get_ebgp_graph',
           'ibgp_routers', 'get_ibgp_graph',
           'initialise_bgp']

import networkx as nx
import AutoNetkit as ank
import logging
LOG = logging.getLogger("ANK")

def ebgp_edges(network):
    """
    Returns eBGP edges once configured from initialise_ebgp

    """
    return ( (s,t) for s,t in network.g_session.edges()
            if network.asn(s) != network.asn(t))

def ibgp_edges(network):
    """ iBGP edges in network 

    >>> network = ank.example_single_as()
    >>> initialise_ibgp(network)
    >>> list(sorted(ibgp_edges(network)))
    [('1a', '1b'), ('1a', '1c'), ('1a', '1d'), ('1b', '1a'), ('1b', '1c'), ('1b', '1d'), ('1c', '1a'), ('1c', '1b'), ('1c', '1d'), ('1d', '1a'), ('1d', '1b'), ('1d', '1c')]
    """
    return ( (s,t) for s,t in network.g_session.edges()
            if network.asn(s) == network.asn(t))

def initialise_ebgp(network):
    """Adds edge for links that have router in different ASes

    >>> network = ank.example_multi_as()
    >>> initialise_ebgp(network)
    >>> network.g_session.edges()
    [('2d', '3a'), ('3a', '1b'), ('1c', '2a')]
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
    if len(network.g_session):
        LOG.warn("Initialising BGP for non-empty session graph. Have you already"
                " specified a session graph?")
        #TODO: throw exception here
        return
    initialise_ebgp(network)
    initialise_ibgp(network)

def ebgp_routers(network):
    """List of all routers with an eBGP link

    >>> network = ank.example_multi_as()
    >>> initialise_ebgp(network)
    >>> ebgp_routers(network)
    ['2d', '3a', '1b', '1c', '2a']
    """
    return list(set(item for pair in ebgp_edges(network) for item in pair))

def ibgp_routers(network):
    """List of all routers with an iBGP link"""
    return list(set(item for pair in ibgp_edges(network) for item in pair))

def get_ebgp_graph(network):
    """Returns graph of eBGP routers and links between them."""
#TODO: see if just use subgraph here for efficiency
    ebgp_graph = network.g_session.subgraph(ebgp_routers(network))
    ebgp_graph.remove_edges_from( ibgp_edges(network))
    return ebgp_graph

def get_ibgp_graph(network):
    """Returns iBGP graph (full mesh currently) for an AS."""
#TODO: see if just use subgraph here for efficiency
    ibgp_graph = network.g_session.subgraph(ibgp_routers(network))
    ibgp_graph.remove_edges_from( ebgp_edges(network))
    return ibgp_graph
