# -*- coding: utf-8 -*-
"""
BGP
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['allocate_dns_servers',
           'dns_list', 'root_dns', 'reverse_subnet', 'rev_dns_identifier']

import AutoNetkit as ank
import networkx as nx

import logging
LOG = logging.getLogger("ANK")

def allocate_dns_servers(network):
    # Remove any previously set DNS servers
    #TODO: use ANK API rather than direct graph access
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


def reverse_subnet(ip_addr, subnet):
    """Returns reverse address for given IP Address"""
    #ToDO: add examples here - this isn't full IP reverse but the subnet
    # part reversed
    #reverse entry depends on prefix length, split and keep entries
    prefixlen = subnet.prefixlen
    split_ip = str(ip_addr).split(".")
    if(prefixlen >= 24):
        #Supernet is class C
        reverse = split_ip[3]
    elif(prefixlen >= 16):
        #Supernet is class B
        reverse = split_ip[3] + "." + split_ip[2]
    elif(prefixlen >= 8):
        #Supernet is class A
        reverse =  split_ip[3] + "." + split_ip[2] + "." + split_ip[1]
    return reverse

def rev_dns_identifier(subnet):
    """ Returns Identifier part of subnet for use in reverse dns itentification.
    Eg 10.1.2.3/8 -> 10
    172.16.1.2/8 -> 16.172
    192.168.0.1/24 -> 0.168.192
    """

    split_sn = str(subnet).split(".")
    prefixlen = subnet.prefixlen

    if(prefixlen == 8):
        identifier = split_sn[0]
    elif(prefixlen == 16):
        identifier = split_sn[1] + "." + split_sn[0]
    elif(prefixlen == 24):
        identifier = (split_sn[2] + "." + split_sn[1] + "." +
                        split_sn[0])

    return identifier
