# -*- coding: utf-8 -*-
"""
DNS
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['allocate_dns_servers',
           'dns_list', 'root_dns', 'reverse_subnet', 'rev_dns_identifier']

import AutoNetkit as ank
import networkx as nx
from netaddr import IPAddress, IPNetwork

import logging
LOG = logging.getLogger("ANK")

def allocate_dns_servers(network):
    # Remove any previously set DNS servers
    #TODO: use ANK API rather than direct graph access
    LOG.debug("Allocating DNS servers")
    for node, data in network.graph.nodes_iter(data=True):
        if 'local_dns' in data:
            del network.graph.node[node]['local_dns']
        if 'global_dns' in data:
            del network.graph.node[node]['global_dns']

    # Marks the global, as well as local DNS server for each AS
    for my_as in ank.get_as_graphs(network):
        central_node = network.central_node(my_as)
        network.graph.node[central_node]['local_dns'] = True

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


#TODO: make more efficient for large networks - eg size of KDL from Zoo
def dns_list(network):
    """Return first central node for each AS ."""
    retval =  dict( (data['asn'], node) for node, data in
                   network.graph.nodes_iter(data=True) if 'local_dns' in data)
    #TODO: check exactly one DNS server per AS allocated
    return retval

def root_dns(network):
    LOG.debug("Allocating root DNS server")
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
        return root_dns_server.pop()


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

