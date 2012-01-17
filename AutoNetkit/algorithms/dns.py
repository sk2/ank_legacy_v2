# -*- coding: utf-8 -*-
"""
DNS

.. warning::

    Work in progress.

Automated hiearchy
===================

There are four levels.

    Connectivity:

    =========   ==============      ======  =========
    Level       Name                Peer    Parent
    ---------   --------------      ------  ---------
    1           Client              None    dns_l2_cluster
    2           Caching Server      ?       asn
    3           AS Server           ?       root
    4           Root                None    None
    =========   ==============      ======  =========

    Records:

    =========   ================================
    Level       Responsibility          
    ---------   -------------------------------- 
    1           None
    2           Caching for clients 
    3           Authoritative for dns_l2_cluster       
    4           Root - announces relevant l3          
    =========   ================================

    dns_l2_cluster is PoP if set, if not is asn

    #TODO: allow levels to be selected:

    =========   ===============================================
    Levels      Meaning          
    ---------   ----------------------------------------------- 
    1           NA
    2           clients (1) connect to root (2)
    3           clients (1) connect to as (3), as to root (4)       
    4           full, as above
    =========   ===============================================


"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen

__all__ = ['allocate_dns_servers', 'get_dns_graph',
        'dns_servers', 'dns_level', 'advertise_links',
        'dns_advertise_link', 'root_dns_servers',
        'dns_auth_servers', 'get_dns_auth_graph',
        'dns_clients', 'dns_auth_children',
        'dns_cache_servers',
        'dns_hiearchy_children', 'dns_hiearchy_parents',
        'reverse_subnet', 'rev_dns_identifier']

import AutoNetkit as ank
import networkx as nx
from netaddr import IPAddress, IPNetwork
import pprint
import itertools
import AutoNetkit.config as config


import logging
LOG = logging.getLogger("ANK")

def allocate_dns_servers(network):
    """Allocates DNS according to rules defined above
    
    TODO: allow 3 level (ie no pop caching, clients connect to AS server)
    TODO: make DNS servers standalone rather that co-hosted with router
    
    TODO: note set dns level on dns graph, but ibgp level on physical graph - inconsistent!
    
    """
    dns_graph = nx.DiGraph()
    dns_advertise_graph = nx.DiGraph()
    LOG.debug("DNS currently disabled")

    dns_levels = config.settings['DNS']['levels']
    if not dns_levels:
        LOG.debug("DNS level 0, disabling DNS for network")
        return

    LOG.info("DNS level set to %s" % dns_levels)
    dns_levels = 4

    def nodes_by_eccentricity(graph):
        if len(graph) == 1:
            return graph.nodes()
# need to crop the global shortest paths otherwise get 
#NetworkXError: Graph not connected: infinite path length
        eccentricities = nx.eccentricity(graph)
        return sorted(eccentricities.keys(), key = lambda n: eccentricities[n])

    def format_asn(asn):
        """Returns unique format for asn, so don't confuse with property of the same,
        eg if ibgp_l2_cluster = 1 in as2, it could match as1 routers as 1==1
        so set asn_1 so 1 != asn_1"""
        return "asn_%s" % asn

    def get_l2_cluster(node):
        """syntactic sugar to access cluster"""
        return dns_graph.node[node].get("dns_l2_cluster")

    def get_l3_cluster(node):
        """syntactic sugar to access cluster"""
        return dns_graph.node[node].get("dns_l3_cluster")

    def level(u):
        return int(dns_graph.node[u]['level'])

    servers_per_l2_cluster = config.settings['DNS']['Server Count']['l2 cluster'] 
    servers_per_l3_cluster = config.settings['DNS']['Server Count']['l3 cluster'] 
    root_dns_servers = config.settings['DNS']['Server Count']['root'] 
    global_eccentricities = nodes_by_eccentricity(network.graph)


#TODO: add count of each cluster occurence so can round servers down - dont want 3 servers in a one router network!

# Add routers, these form the level 1 clients
    dns_graph.add_nodes_from(network.graph.nodes(), level=1)
    for node, data in network.graph.nodes(data=True):
        #TODO: the cluster should never be manually set, so can remove checks
        if not data.get("dns_l2_cluster"):
            dns_graph.node[node]['dns_l2_cluster'] = data.get("pop") or format_asn(network.asn(node))
        if not data.get("dns_l3_cluster"):
            dns_graph.node[node]['dns_l3_cluster'] = format_asn(network.asn(node))


    for my_as in ank.get_as_graphs(network):
        asn = my_as.asn
        if not nx.is_strongly_connected(my_as):
            LOG.info("AS%s not fully connected, skipping DNS configuration" % asn)
            continue


        l2_clusters = list(set(dns_graph.node[n].get("dns_l2_cluster") for n in my_as))
        for l2_cluster in l2_clusters:
            for index in range(servers_per_l2_cluster):
                label = "l2_%s_dns_%s" % (l2_cluster, index+1)
                if l2_cluster == format_asn(asn):
# Don't put asn into server name twice "AS2_asn_2_l2dns_1" vs "asn_2_l2dns_1"
                    server_name = "%s_l2dns_%s" % (l2_cluster, index+1)
                else:
                    server_name = "AS%s_%s_l2dns_%s" % (asn, l2_cluster, index+1)
#TODO: see what other properties to retain
                node_name = network.add_device(server_name, asn=asn, 
                        device_type='server', label=label)
                dns_graph.add_node(node_name, level=2, dns_l2_cluster=l2_cluster,
                        asn = asn, dns_l3_cluster = format_asn(asn))

        for index in range(servers_per_l3_cluster):
                label = "l3_%s_dns_%s" % (asn, index+1)
                server_name = "AS%s_l3dns_%s" % (asn, index+1)
                node_name = network.add_device(server_name, asn=asn, 
                        device_type='server', label=label)
#TODO: check if need to add l2 here - was coded before, possible mistake?
                dns_graph.add_node(node_name, level=3, 
                        asn = asn, dns_l3_cluster = format_asn(asn))
    
    # and level 4 connections
#TODO: need to determine the right place to put the server - order issue between allocating for root as need an ASN for the device before  know best place - for now use asn = 1, and move if needed
    for index in range(root_dns_servers):
        attach_point = global_eccentricities.pop()
        server_name = "root_dns_%s" % (index+1)
        asn = ank.asn(attach_point)
        LOG.debug("Attaching %s to %s in %s" % (server_name, ank.label(attach_point), asn))
        node_name = network.add_device(server_name, asn=asn, device_type='server')
        network.add_link(node_name, attach_point)
        dns_graph.add_node(node_name, level=4)
        
    # now connect
#TODO: scale to handle multiple levels same as ibgp (see doco at start for details)
    edges_to_add = []
    all_edges = [ (s,t) for s in dns_graph for t in dns_graph if s != t]
    same_l3_cluster_edges = [ (s,t) for (s,t) in all_edges if 
                    get_l3_cluster(s) == get_l3_cluster(t) != None]
    same_l2_cluster_edges = [ (s,t) for (s,t) in same_l3_cluster_edges if 
                    get_l2_cluster(s) == get_l2_cluster(t) != None]
    
# l1 -> l2 same l2 cluster
    edges_to_add += [(s,t, 'up') for (s,t) in same_l2_cluster_edges
            if level(s) == 1 and level(t) == 2]
    # l2 -> l2 ???

# l2 -> l3
    edges_to_add += [(s,t, 'up') for (s,t) in same_l3_cluster_edges
            if level(s) == 2 and level(t) == 3]

# l3 -> l4
    edges_to_add += [(s,t, 'up') for (s,t) in all_edges
            if level(s) == 3 and level(t) == 4]
    
    # format into networkx format
    edges_to_add = ( (s,t, {'dns_dir': dns_dir}) for (s, t, dns_dir) in edges_to_add)
    dns_graph.add_edges_from(edges_to_add)

# and create attach points
# take advantage of Python sorts being stable
# refer http://wiki.python.org/moin/HowTo/Sorting
#TODO: note assumes routers are level 1 - need to also check type is router!
    routers = set(network.routers())
    devices = dns_graph.nodes()
    devices = sorted(devices, key= get_l2_cluster)
    devices = sorted(devices, key= get_l3_cluster)
    devices = sorted(devices, key= ank.asn)
    for asn, asn_devices in itertools.groupby(devices, key = ank.asn):
# if no asn set, then root server, which has already been allocated
        if asn:
            # asn is set, look at l3 groups
            for l3_cluster, l3_cluster_devices in itertools.groupby(asn_devices, key = get_l3_cluster):
                if not l3_cluster:
                    #TODO: see why getting empty cluster
                    continue
                l3_cluster_devices = set(l3_cluster_devices)
                l3_cluster_servers = set(n for n in l3_cluster_devices if level(n) == 3)
                l3_cluster_routers = set(n for n in l3_cluster_devices if n in routers)

                l3_cluster_physical_graph = network.graph.subgraph(l3_cluster_routers)
                l3_cluster_eccentricities = nodes_by_eccentricity(l3_cluster_physical_graph)
# Cycle in event more servers to attach than routers
                l3_cluster_eccentricities = itertools.cycle(l3_cluster_eccentricities)
                for server in l3_cluster_servers:
                    attach_point = l3_cluster_eccentricities.next()
                    LOG.debug("Attaching %s to %s in %s" % (ank.label(server), 
                        ank.label(attach_point), asn))
                    network.add_link(server, attach_point)

                l1l2_devices = l3_cluster_devices - set(l3_cluster_servers)
# resort after set operations for groupby to work correctly
                l1l2_devices = sorted(l1l2_devices, key= get_l2_cluster)
                for l2_cluster, l2_cluster_devices in itertools.groupby(l1l2_devices, key = get_l2_cluster):
                    l2_cluster_devices = set(l2_cluster_devices)
                    l2_cluster_servers = set(n for n in l2_cluster_devices if level(n) == 2)
                    l2_cluster_routers = set(n for n in l2_cluster_devices if level(n) == 1 and n in routers)
                    l2_cluster_physical_graph = network.graph.subgraph(l2_cluster_routers)
                    l2_cluster_eccentricities = nodes_by_eccentricity(l2_cluster_physical_graph)
                    # Cycle in event more servers to attach than routers
                    l2_cluster_eccentricities = itertools.cycle(l2_cluster_eccentricities)
                    for server in l2_cluster_servers:
                        attach_point = l2_cluster_eccentricities.next()
                        LOG.debug("Attaching %s to %s in %s" % (ank.label(server), 
                            ank.label(attach_point), asn))
                        network.add_link(server, attach_point)


#TODO: authoritative might need to be a graph also
# setup domains

    for server in dns_servers(network):
        children = dns_auth_children(server)
        if len(children):
# does auth, set domain
            network.g_dns.node[server]['domain'] = "AS%s" % server.asn

# TODO: handle different levels
# in 3 level model, l3 servers advertise for AS
    for my_as in ank.get_as_graphs(network):
        devices = [ n for n in my_as]
        as_l3_servers = (n for n in my_as if level(n) == 3)
        edges = itertools.product(devices, as_l3_servers)
        dns_advertise_graph.add_edges_from(edges)

    network.g_dns = dns_graph
    network.g_dns_auth = dns_advertise_graph

def dns_advertise_link(src, dst):
# find servers responsible for src
    for src_server in dns_auth_parents(src):
        add_dns_auth_child(src_server, dst)

def dns_hiearchy_children(node):
    return node.network.g_dns.predecessors(node)

def dns_hiearchy_parents(node):
    return node.network.g_dns.successors(node)

def add_dns_auth_child(parent, child):
    parent.network.g_dns_auth.add_edge(child, parent)
  
def dns_auth_parents(node):
    """Handles case of no parents having been allocated"""
    try:
        return node.network.g_dns_auth.successors(node)
    except nx.exception.NetworkXError:
        return []

def dns_auth_children(node):
    return node.network.g_dns_auth.predecessors(node)

def root_dns_servers(network):
    return (n for n in network.servers() if dns_level(n) == 4)

def dns_cache_servers(network):
    return (n for n in network.servers() if dns_level(n) == 2)

def advertise_links(node):
    auth_children = dns_auth_children(node)
    auth_subgraph = node.network.graph.subgraph(auth_children)
    edges = auth_subgraph.edges()
    if edges:
        return (ank.network.link_namedtuple(node.network, src, dst) for (src, dst) in edges)
    else:
        return []

def is_dns_server(network, node):
# if has children is server
# note could also be child to own parent
    pass

def is_dns_client(network, node):
# if has parent is client 
    # note could also be server to own children
    pass

def dns_level(node):
    return node.network.g_dns.node[node].get("level")

def dns_servers(network):
    """Servers that have DNS level > 1"""
    return (n for n in network.g_dns.nodes_iter() if dns_level(n) > 1)

def dns_clients(network):
    """Devices that have DNS level == 1"""
    return (n for n in network.g_dns.nodes_iter() if dns_level(n) == 1)

def dns_auth_servers(network):
    """Servers that have auth children"""
    return (n for n in dns_servers(network) if len(dns_auth_children(n)))

def get_dns_graph(network):
    return network.g_dns

def get_dns_auth_graph(network):
    return network.g_dns_auth

def reverse_subnet(link, prefixlen):
    """Returns reverse address for given IP Address

    * w.x.y.z/prefixlen
    * prefixlen >= 24 -> return z
    * 24 >= prefixlen >= 16 -> return z.y
    * 16 >= prefixlen >= 8 -> return z.y.w
    * 8 >= prefixlen  -> return z.y.x.w
    
    >>> reverse_subnet(IPAddress("10.0.0.22"), 16)
    '22.0'
    >>> reverse_subnet(IPAddress("10.0.0.21"), 16)
    '21.0'
    >>> reverse_subnet(IPAddress("10.0.0.129"), 16)
    '129.0'
    >>> reverse_subnet(IPAddress("1.2.3.4"), 5)
    '4.3.2.1'
    >>> reverse_subnet(IPAddress("1.2.3.4"), 15)
    '4.3.2'
    >>> reverse_subnet(IPAddress("1.2.3.4"), 20)
    '4.3'
    >>> reverse_subnet(IPAddress("1.2.3.4"), 26)
    '4'
    
    """
    octets = link.ip.words
    return ".".join(str(octets[x]) for x in range(3, prefixlen/8-1, -1))
   
def rev_dns_identifier(subnet):
    """ Returns Identifier part of subnet for use in reverse dns identification.

    >>> rev_dns_identifier(IPNetwork("10.1.2.3/8"))
    '10'

    >>> rev_dns_identifier(IPNetwork("172.16.1.2/16"))
    '16.172'

    >>> rev_dns_identifier(IPNetwork("192.168.0.1/24"))
    '0.168.192'

    Can only handle classful addreses, expect nothing if prefixlen is not divisible by 8
    >>> rev_dns_identifier(IPNetwork("192.168.0.1/22"))


    """
    if subnet.prefixlen % 8 != 0:
# Can only do classful subnets (config is too complicated otherwise)
        LOG.warn("Reverse DNS can only handle /8, /16, /24, unable to process %s"
                % subnet)
        return

    reversed = subnet.network.reverse_dns.split(".")
# Drop the first/second octets if class A/B
    if subnet.prefixlen == 8:
        reversed = reversed[1:]
    elif subnet.prefixlen == 16:
        reversed = reversed[2:]
    return ".".join(reversed)
