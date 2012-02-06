# -*- coding: utf-8 -*-
"""
BGP

.. warning::

    Work in progress.

eBGP
====
eBGP is configured automatically, if there is an edge in the physical graph between two nodes that belong to different Autonomous Systems:

``if asn(s) != asn(t) for s,t in edges``

iBGP
====

    * Peer column refers to connections at the same level (eg 2->2)
    * Parent column refers to connections to level above (eg 1->2)
    * There are no child connections (eg 3->2)
    * as_cluster is the entire AS

    l2_cluster can be manually specified. If not specified, it defaults to being a PoP.
    If no PoPs specified, it defaults to being the AS.

    l3_cluster defaults to asn if not set: we connect the l2 rr to all l3 rrs in the same AS.

    Three types of ibgp connection:

    * *up* to a server
    * *down* to a client
    * *over* to a peer

    .. note::

        If the network only has level 1 route-reflectors, then the connections are labelled as *peer*

    The below tables show the matching attributes to use.
    
    1-level:

    =========   ==========          ==========
    Level       Peer                Parent
    ---------   ----------          ----------
    1           asn                 None      
    =========   ==========          ==========

    2-level:

    =========   ==========          ==========
    Level       Peer                Parent
    ---------   ----------          ----------
    1           None                l2_cluster
    2           asn                 None
    =========   ==========          ==========

    3-level:

    =========   =============       ===========
    Level       Peer                Parent
    ---------   -------------       -----------
    1           None                l2_cluster
    2           l2_cluster          l3_cluster
    3           asn                 None 
    =========   =============       ===========

"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['ebgp_routers', 'get_ebgp_graph',
        'ebgp_edges',
           'ibgp_routers', 'get_ibgp_graph',
           'bgp_routers',
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
    if not network.g_session.graph.get('ebgp_initialised'):
        initialise_ebgp(network)
    return ( (s,t) for s,t in network.g_session.edges() if s.asn != t.asn)

def ibgp_edges(network):
    """ iBGP edges in network 
#TODO: use sets here

    >>> network = ank.example_single_as()
    >>> list(sorted(ibgp_edges(network)))
    [(1a.AS1, 1b.AS1), (1a.AS1, 1c.AS1), (1a.AS1, 1d.AS1), (1b.AS1, 1a.AS1), (1b.AS1, 1c.AS1), (1b.AS1, 1d.AS1), (1c.AS1, 1a.AS1), (1c.AS1, 1b.AS1), (1c.AS1, 1d.AS1), (1d.AS1, 1a.AS1), (1d.AS1, 1b.AS1), (1d.AS1, 1c.AS1)]

    """
    if not network.g_session.graph.get('ibgp_initialised'):
        initialise_ibgp(network)
    return ( (s,t) for s,t in network.g_session.edges() if s.asn == t.asn)

def configure_ibgp_rr(network):
    """Configures route-reflection properties based on work in (NEED CITE).

    Note: this currently needs ibgp_level to be set globally for route-reflection to work.
    Future work will implement on a per-AS basis.
    """
    LOG.debug("Configuring iBGP route reflectors")
# Add all nodes from physical graph
#TODO: if no 
    network.g_session.add_nodes_from(network.graph)

    def level(u):
        return int(network.graph.node[u]['ibgp_level'])

    def format_asn(asn):
        """Returns unique format for asn, so don't confuse with property of the same,
        eg if ibgp_l2_cluster = 1 in as2, it could match as1 routers as 1==1
        so set asn_1 so 1 != asn_1"""
        return "asn_%s" % asn

    default_ibgp_level = 1

    #TODO: make "asn" eg "asn_1" as could conflict if asn=1 and ibgp_l2_cluster = 1 elsewhere and match the same
    for my_as in ank.get_as_graphs(network):
        #TODO: for neatness, look at redefining the above functions inside here setting my_as as network
        asn = my_as.name
        nodes_without_level_set = [n for n in my_as if not network.graph.node[n].get('ibgp_level')]
        if len(nodes_without_level_set):
                LOG.debug("Setting default ibgp_level of %s for nodes %s" % (default_ibgp_level,
                    ", ".join(str(n) for n in nodes_without_level_set)))
                for node in nodes_without_level_set:
                    network.graph.node[node]['ibgp_level'] = default_ibgp_level

        max_ibgp_level = max(level(n) for n in my_as)
        LOG.debug("Max ibgp level for %s is %s" % (my_as.asn, max_ibgp_level))
        if max_ibgp_level >= 2:
            for node, data in my_as.nodes(data=True):
                if not data.get("ibgp_l2_cluster"):
                    # due to boolean evaluation will set in order from left to right
                    network.graph.node[node]['ibgp_l2_cluster'] = data.get("pop") or format_asn(asn)

                if max_ibgp_level == 3 and not data.get("ibgp_l3_cluster"):
                        # due to boolean evaluation will set in order from left to right
                        network.graph.node[node]['ibgp_l3_cluster'] = format_asn(asn)
# Now connect
        edges_to_add = []
# List of edges for easier iteration (rather than doing each time)
        as_edges = [ (s,t) for s in my_as for t in my_as if s != t]
        if max_ibgp_level > 1:
            same_l2_cluster_edges = [ (s,t) for (s,t) in as_edges if 
                    network.graph.node[s]['ibgp_l2_cluster'] == network.graph.node[t]['ibgp_l2_cluster']]
        if max_ibgp_level > 2:
            same_l3_cluster_edges = [ (s,t) for (s,t) in as_edges if
                    network.graph.node[s]['ibgp_l3_cluster'] == network.graph.node[t]['ibgp_l3_cluster']]

        if max_ibgp_level == 1:
            #1           asn                 None      
            edges_to_add += [(s, t, 'peer') for (s,t) in as_edges]
        else:
            edges_to_add += [(s,t, 'up') for (s,t) in same_l2_cluster_edges
                    if level(s) == 1 and level(t) == 2]
            edges_to_add += [(s,t, 'down') for (s,t) in same_l2_cluster_edges
                    if level(s) == 2 and level(t) == 1]

        if max_ibgp_level == 2:
            edges_to_add += [(s, t, 'peer') for (s,t) in as_edges 
                    if level(s) == level(t) == 2]
        elif max_ibgp_level == 3:
            edges_to_add += [(s,t, 'peer') for (s,t) in same_l2_cluster_edges
                    if level(s) == level(t) == 2]
            edges_to_add += [(s,t, 'up') for (s,t) in same_l3_cluster_edges
                    if level(s) == 2 and level(t) == 3]
            edges_to_add += [(s,t, 'down') for (s,t) in same_l3_cluster_edges
                    if level(s) == 3 and level(t) == 2]
            edges_to_add += [(s, t, 'peer') for (s,t) in same_l3_cluster_edges 
                    if level(s) == level(t) == 3]

        # format into networkx format
        edges_to_add = [ (s,t, {'rr_dir': rr_dir}) for (s, t, rr_dir) in edges_to_add]
        LOG.debug("iBGP edges %s" % pprint.pformat(edges_to_add))
        network.g_session.add_edges_from(edges_to_add)

    for node, data in network.graph.nodes(data=True):
# is route_reflector if level > 1
        network.graph.node[node]['route_reflector'] = int(data.get("ibgp_level")) > 1

def initialise_ebgp(network):
    """Adds edge for links that have router in different ASes

    >>> network = ank.example_multi_as()
    >>> initialise_ebgp(network)
    >>> sorted(network.g_session.edges())
    [(1b.AS1, 3a.AS3), (1c.AS1, 2a.AS2), (2a.AS2, 1c.AS1), (2d.AS2, 3a.AS3), (3a.AS3, 1b.AS1), (3a.AS3, 2d.AS2)]

    """
    LOG.debug("Initialising eBGP")
    edges_to_add = ( (src, dst) for src, dst in network.graph.edges()
            if network.asn(src) != network.asn(dst))
    edges_to_add = list(edges_to_add)
    network.g_session.add_edges_from(edges_to_add)
    network.g_session.graph['ebgp_initialised'] = True

def initialise_ibgp(network):
    LOG.debug("Initialising iBGP")
    configure_ibgp_rr(network)
    network.g_session.graph['ibgp_initialised'] = True

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

def bgp_routers(network):
    if not network.g_session.graph.get('ebgp_initialised'):
        initialise_ebgp(network)
    return (n for n in network.g_session)

def ebgp_routers(network):
    """List of all routers with an eBGP link

    >>> network = ank.example_multi_as()
    >>> sorted(ebgp_routers(network))
    [1b.AS1, 1c.AS1, 2a.AS2, 2d.AS2, 3a.AS3]

    """
    if not network.g_session.graph.get('ebgp_initialised'):
        initialise_ebgp(network)
    return list(set(item for pair in ebgp_edges(network) for item in pair))

def ibgp_routers(network):
    """List of all routers with an iBGP link"""
    if not network.g_session.graph.get('ibgp_initialised'):
        initialise_ibgp(network)
    return list(set(item for pair in ibgp_edges(network) for item in pair))

def get_ebgp_graph(network):
    """Returns graph of eBGP routers and links between them."""
#TODO: see if just use subgraph here for efficiency
    if not network.g_session.graph.get('ebgp_initialised'):
        initialise_ebgp(network)
    ebgp_graph = network.g_session.subgraph(ebgp_routers(network))
    ebgp_graph.remove_edges_from( ibgp_edges(network))
    return ebgp_graph

def get_ibgp_graph(network):
    """Returns iBGP graph (full mesh currently) for an AS."""
#TODO: see if just use subgraph here for efficiency
    if not network.g_session.graph.get('ibgp_initialised'):
        initialise_ibgp(network)
    ibgp_graph = network.g_session.subgraph(ibgp_routers(network))
    ibgp_graph.remove_edges_from( ebgp_edges(network))
    return ibgp_graph
