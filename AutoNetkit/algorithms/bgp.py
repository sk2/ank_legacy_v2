# -*- coding: utf-8 -*-
"""
BGP


Route-Reflection level rules:

    * Peer column refers to connections at the same level (eg 2->2)
    * Parent column refers to connections to level above (eg 1->2)
    * There are no child connections (eg 3->2)
    * as_cluster is the entire AS

    2-level:

    =========   =========       =======
    Level       Peer            Parent
    ---------   ---------       -------
    1           None            l2_cluster
    2           as_cluster      None
    =========   =========       =======

    3-level:

    =========   =============       ===========
    Level       Peer                Parent
    ---------   -------------       -----------
    1           None                l2_cluster
    2           l2_cluster          l3_cluster
    3           as_cluster          None 
    =========   =============       ===========


"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['ebgp_routers', 'get_ebgp_graph',
           'ibgp_routers', 'get_ibgp_graph',
           'initialise_bgp']

import networkx as nx
import pprint
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

def ibgp_level_set_for_all_nodes(network):
    """Test if ibgp_level property set for all nodes in network.
    Warn user if ibgp_level set for some nodes, but not for all."""
    ibgp_set_per_node = [d.get("ibgp_level") for n, d in network.graph.nodes(data=True)]
    are_all_set = all(ibgp_set_per_node)
    if are_all_set != any(ibgp_set_per_node):
# some nodes have ibgp_level set, but not all nodes, warn possible error
        set_node_count =  sum(True for n in ibgp_set_per_node if n)
        total_nodes = len(ibgp_set_per_node)
        LOG.warn("Possible mistake: ibgp_level is set for %s/%s nodes. Using full-mesh iBGP topology." 
                % (set_node_count, total_nodes))
    return are_all_set

def configure_ibgp_rr(network):
    """Configures route-reflection properties based on work in (NEED CITE).

    Note: this currently needs ibgp_level to be set globally for route-reflection to work.
    Future work will implement on a per-AS basis.




    """
    LOG.debug("Configuring iBGP route reflectors")



    edges_to_add = []
    for (s,t) in ((s,t) for s in network.graph.nodes() for t in network.graph.nodes() 
            if (s!= t # not same node
                and network.asn(s) == network.asn(t) # Only iBGP for nodes in same ASes
                )):
        s_level = network.ibgp_level(s)
        t_level = network.ibgp_level(t)
# Intra-PoP
#TODO: also make Intra-Cluster
        if (
                (network.pop(s) == network.pop(t)) # same PoP
                or (network.ibgp_cluster(s) == network.ibgp_cluster(t) != None) # same cluster and cluster is set
                ):
            if s_level == t_level == 1:
                # client to client: do nothing
                pass
            elif (s_level == 1) and (t_level == 2):
                # client -> server: up
                edges_to_add.append( (s, t, {'rr_dir': 'up'}) )
            elif (s_level == 2) and (t_level == 1):
                # server -> client: down
                edges_to_add.append( (s, t, {'rr_dir': 'down'}) )
            elif s_level == t_level == 2:
                # server -> server: over
                edges_to_add.append( (s, t, {'rr_dir': 'over'}) )
        else:
# Inter-PoP
            if s_level == t_level == 2:
                edges_to_add.append( (s, t, {'rr_dir': 'over'}) )


    # Add with placeholders for ingress/egress policy
    network.g_session.add_edges_from(edges_to_add)

    # And mark route-reflector on physical graph
    for node, data in network.graph.nodes(data=True):
        route_reflector = False
        if int(data.get("ibgp_level")) > 1:
            route_reflector = True
        network.graph.node[node]['route_reflector'] = route_reflector

def initialise_ebgp(network):
    """Adds edge for links that have router in different ASes

    >>> network = ank.example_multi_as()
    >>> initialise_ebgp(network)
    >>> network.g_session.edges()
    [('2d', '3a'), ('3a', '1b'), ('1c', '2a')]
    """
    LOG.debug("Initialising eBGP")
    edges_to_add = ( (src, dst) for src, dst in network.graph.edges()
            if network.asn(src) != network.asn(dst))
    edges_to_add = list(edges_to_add)
    network.g_session.add_edges_from(edges_to_add)

def initialise_ibgp(network):
    LOG.debug("Initialising iBGP")
    if ibgp_level_set_for_all_nodes(network):
        configure_ibgp_rr(network)
    else:
# Full mesh
        edges_to_add = ( (s,t) for s in network.graph for t in network.graph 
                if (s is not t and
                    network.asn(s) == network.asn(t)))
        network.g_session.add_edges_from(edges_to_add, rr_dir = 'peer')

def initialise_bgp_sessions(network):
    """ add empty ingress/egress lists to each session.
    Note: can't do in add_edges_from due to:
    http://www.ferg.org/projects/python_gotchas.html#contents_item_6
    """
    LOG.debug("Initialising iBGP sessions")
    for (u,v) in network.g_session.edges():
        network.g_session[u][v]['ingress'] = []
        network.g_session[u][v]['egress'] = []

    return

def initialise_bgp_attributes(network):
    LOG.debug("Initialising BGP attributes")
    for node in network.g_session:
        network.g_session.node[node]['tags'] = {}
        network.g_session.node[node]['prefixes'] = {}


def initialise_bgp(network):
    LOG.debug("Initialising BGP")
    if len(network.g_session):
        LOG.warn("Initialising BGP for non-empty session graph. Have you already"
                " specified a session graph?")
        #TODO: throw exception here
        return
    initialise_ebgp(network)
    initialise_ibgp(network)
    initialise_bgp_sessions(network)
    initialise_bgp_attributes(network)

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
