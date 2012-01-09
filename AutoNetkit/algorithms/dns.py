# -*- coding: utf-8 -*-
"""
DNS

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
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['allocate_dns_servers', 'get_dns_graph',
           'dns_list', 'root_dns', 'reverse_subnet', 'rev_dns_identifier']

import AutoNetkit as ank
import networkx as nx
from netaddr import IPAddress, IPNetwork
import pprint
import itertools
import random

import logging
LOG = logging.getLogger("ANK")

def allocate_dns_servers(network):
    # Remove any previously set DNS servers
    #TODO: use ANK API rather than direct graph access
    """ TODO: discuss with Hung - levels, what if both 3 (root) and 2 (local as)"""
    LOG.debug("Allocating DNS servers")
    dns_graph = nx.DiGraph()
    dns_graph.add_nodes_from(network.graph)
    
    # remove existing dns servers
    for node, data in network.graph.nodes_iter(data=True):
        if 'local_dns' in data:
            del network.graph.node[node]['local_dns']
        if 'global_dns' in data:
            del network.graph.node[node]['global_dns']

    root_dns_servers = set()
    if not nx.is_strongly_connected(network.graph):
        LOG.info("Network not fully connected, skipping DNS")
        return

    if nx.is_strongly_connected(network.graph):
        global_dns =  nx.center(network.graph)[0]
    else:
        # Network not fully connected, so central DNS server is arbitary choice
        # choose a server from the largest connected component
        LOG.debug("Network not strongly connected, choosing root DNS from "
                 " largest connected subgraph")
        connected_components = nx.strongly_connected_component_subgraphs(
            network.graph)
        if len(connected_components) == len(network.graph):
            LOG.warn("Graph has no connected nodes, not allocating DNS")
            return
        # Find largest component
        connected_components.sort(key=len, reverse=True)
        largest_subgraph = connected_components[0]
        # Choose central node in this subgraph
        if len(largest_subgraph) == 1:
            global_dns = largest_subgraph.nodes().pop()
        else:
            global_dns = nx.center(largest_subgraph)[0]
    network.graph.node[global_dns]['global_dns'] = True

    # Marks the global, as well as local DNS server for each AS
    per_as_server_count = 1
    all_dns_servers = set()
    for my_as in ank.get_as_graphs(network):
        local_dns_servers = set()
        if len(my_as) == 1:
# add only router as DNS server
            local_dns_servers.update(my_as.nodes())
        else:
            if not nx.is_strongly_connected(my_as):
                # TODO: make select a number
                LOG.info("AS%s is not fully connected, selecting random DNS server" % asn)
                local_dns_servers.update(random.choice(my_as.nodes()))
                continue
            eccentricities = nx.eccentricity(my_as)
            eccentricities = sorted(eccentricities.keys(), 
                reverse=True, key=lambda x: eccentricities[x])
            local_dns_servers.update(eccentricities[:per_as_server_count])
# legacy - choose first server to use
        local_dns = list(local_dns_servers)[0]
        network.graph.node[local_dns]['local_dns'] = True
# end legacy
# Mark all other nodes in AS to point to this central node
        LOG.debug("DNS server(s) for AS %s are %s" % (my_as.asn, 
            ", ".join(network.label(s) for s in local_dns_servers)))
        all_dns_servers.update(local_dns_servers)

# Now connect
        client_nodes = (n for n in my_as if n not in local_dns_servers)
        client_sessions = itertools.product(client_nodes, local_dns_servers)
        dns_graph.add_edges_from(client_sessions)

#TODO: allow this to scale to more levels in future

# Eccentricities are dictionary, key=node, value=eccentricity
# Convert this into a list of nodes sorted by most eccentric to least eccentricities
    if len(all_dns_servers) == 1:
# Single root DNS server
        root_dns_servers.update(all_dns_servers)
    else:
        eccentricities = nx.eccentricity(network.graph,
# Need to give nodes as a list, if set is hashable so nx tries to match as node
                list(all_dns_servers))
        eccentricities = sorted(eccentricities.keys(), 
                reverse=True, key=lambda x: eccentricities[x])
        root_server_count = 2
        root_dns_servers.update(eccentricities[:root_server_count])
    LOG.debug("DNS Root servers are %s" % ", ".join(network.fqdn(s) 
        for s in root_dns_servers))

    #TODO: do we connect root DNS servers together?
    client_sessions = itertools.product(local_dns_servers, root_dns_servers)
    dns_graph.add_edges_from(client_sessions)
    network.g_dns = dns_graph
    dns_allocate_v2(network)


def dns_allocate_v2(network):
    """Allocates DNS according to rules defined above
    
    TODO: allow 3 level (ie no pop caching, clients connect to AS server)
    TODO: make DNS servers standalone rather that co-hosted with router
    
    TODO: note set dns level on dns graph, but ibgp level on physical graph - inconsistent!
    
    """
    dns_graph = nx.DiGraph()

    def format_asn(asn):
        """Returns unique format for asn, so don't confuse with property of the same,
        eg if ibgp_l2_cluster = 1 in as2, it could match as1 routers as 1==1
        so set asn_1 so 1 != asn_1"""
        return "asn_%s" % asn

    def get_l2_cluster(node):
        """syntactic sugar to access cluster"""
        return dns_graph.node[node].get("dns_l2_cluster")

    def level(u):
        return int(dns_graph.node[u]['level'])

    servers_per_l2_cluster = 1
    servers_per_l3_cluster = 1
    servers_per_l4_cluster = 2

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
# Break into dns_l2_cluster
            """
        nodes = sorted(my_as.nodes(), key= get_l2_cluster)
        for l2_cluster, g in itertools.groupby(nodes, key = get_l2_cluster):
            cluster_nodes = list(g)
            """

        l2_clusters = list(set(dns_graph.node[n].get("dns_l2_cluster") for n in my_as))
        for l2_cluster in l2_clusters:
            for index in range(servers_per_l2_cluster):
                server_name = "AS%s_%s_l2dns_%s" % (asn, l2_cluster, index+1)
                dns_graph.add_node(server_name, level=2, dns_l2_cluster=l2_cluster,
                        dns_l3_cluster = format_asn(asn))
# add to physical graph

        """
        #TODO: work out appropriate attach points based on groups
#TODO: use eccentricities rather than just degree to choose location
        nodes_by_degree = sorted(my_as.nodes(), key = lambda node: my_as.degree(node))
        cluster_attach_points = nodes_by_degree[:servers_per_l3_cluster]
        for index, node in enumerate(cluster_attach_points):
            pass
        #TODO: wrap this in a function
        server_label = "%s_dns_%s" % (l2_cluster, index+1)
        network.graph.add_node(server_name, label=server_label, 
                platform = "NETKIT",
                type = 'dns_server',
                pop=network.pop(node), asn=asn)
        network.graph.add_edge(server_name, node)
        network.graph.add_edge(node, server_name)
        """
        for index in range(servers_per_l3_cluster):
                server_name = "AS%s_l3dns_%s" % (asn, index+1)
                dns_graph.add_node(server_name, level=3, 
                        dns_l3_cluster = format_asn(asn))
    
    # and level 4 connections
    for index in range(servers_per_l4_cluster):
            server_name = "root_dns_%s" % (index+1)
            dns_graph.add_node(server_name, level=4)
        
    # now connect
#TODO: scale to handle multiple levels same as ibgp (see doco at start for details)
    edges_to_add = []
    all_edges = [ (s,t) for s in dns_graph for t in dns_graph if s != t]
    same_l3_cluster_edges = [ (s,t) for (s,t) in all_edges if 
                    dns_graph.node[s].get('dns_l3_cluster') == dns_graph.node[t].get('dns_l3_cluster') != None]
    same_l2_cluster_edges = [ (s,t) for (s,t) in same_l3_cluster_edges if 
                    dns_graph.node[s].get('dns_l2_cluster') == dns_graph.node[t].get('dns_l2_cluster') != None]
    

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

    network.g_dns = dns_graph

#TODO: also need to connect DNS servers into network, allocate IPs, etc


def is_dns_server(network, node):
# if has children is server
# note could also be child to own parent
    pass

def is_dns_client(network, node):
# if has parent is client 
    # note could also be server to own children
    pass



def get_dns_graph(network):
    return network.g_dns

#TODO: make more efficient for large networks - eg size of KDL from Zoo
def dns_list(network):
    """Return first central node for each AS ."""
    retval =  dict( (data['asn'], node) for node, data in
                   network.graph.nodes_iter(data=True) if 'local_dns' in data)
    #TODO: check exactly one DNS server per AS allocated
    return retval

def root_dns(network):
    LOG.debug("Allocating root DNS server")
    root_dns_servers = [(n,d) for n,d in network.g_dns.out_degree().items()] 

    root_dns_servers = [n for n,d in network.g_dns.out_degree().items() if d==0] 
    root_dns_server = [node for node,data in network.graph.nodes_iter(data=True)
                       if 'global_dns' in data]
    if len(root_dns_server) < 1:
        # No DNS server allocated
        logging.warn("No global DNS server allocated")
        return None
    elif len(root_dns_server) > 1:
        logging.warn("More than one global DNS server allocated")
        # return last server (order unimportant as should only have one)
        return root_dns_server.pop()
    else:
        # Exactly one allocated, remove from list
        retval =  root_dns_server.pop()
        return retval


def reverse_subnet(ip_addr, prefixlen):
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
    octets = ip_addr.words
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

# /8 -> return first octet, /16 -> first two, /24 -> first 3
    last_octet = subnet.prefixlen/8-1  # index of last octet to include
    octets = IPAddress(subnet.network).words
    return ".".join(str(octets[x]) for x in range(last_octet, -1, -1))

