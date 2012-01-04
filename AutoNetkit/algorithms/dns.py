# -*- coding: utf-8 -*-
"""
DNS
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

    if nx.is_strongly_connected(network.graph):
        global_dns =  nx.center(network.graph)[0]
    else:
        # Network not fully connected, so central DNS server is arbitary choice
        # choose a server from the largest connected component
        LOG.debug("Network not strongly connected, choosing root DNS from "
                 " largest connected subgraph")
        connected_components = nx.strongly_connected_component_subgraphs(
            network.graph)
        # Find largest component
        connected_components.sort(key=len, reverse=True)
        largest_subgraph = connected_components[0]
        # Choose central node in this subgraph
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
            eccentricities = nx.eccentricity(my_as)
            eccentricities = sorted(eccentricities.keys(), 
                reverse=True, key=lambda x: eccentricities[x])
            local_dns_servers.update(eccentricities[:per_as_server_count])
# legacy - choose first server to use
        local_dns = list(local_dns_servers)[0]
        network.graph.node[local_dns]['local_dns'] = True
# end legacy
# Mark all other nodes in AS to point to this central node
        LOG.debug("DNS server(s) for AS %s are %s" % (my_as.name, 
            ", ".join(network.label(s) for s in local_dns_servers)))
        all_dns_servers.update(local_dns_servers)

# Now connect
        client_nodes = (n for n in my_as if n not in local_dns_servers)
        client_sessions = itertools.product(client_nodes, local_dns_servers)
        dns_graph.add_edges_from(client_sessions)

#TODO: allow this to scale to more levels in future

# Eccentricities are dictionary, key=node, value=eccentricity
# Convert this into a list of nodes sorted by most eccentric to least eccentric
    
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

# also allocate to graph

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

