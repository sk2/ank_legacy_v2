# -*- coding: utf-8 -*-
"""
Netkit Allocations
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['allocate_to_netkit_hosts', 'netkit_host', 'netkit_hostname',
          'netkit_hosts']

import AutoNetkit as ank
import networkx as nx

import logging
LOG = logging.getLogger("ANK")

def allocate_to_netkit_hosts(network):
    # Remove any previously set DNS servers
    #TODO: use ANK API rather than direct graph access
    for node in network.graph.nodes_iter():
        network.graph.node[node]['netkit_host'] = 1

def netkit_host(network, node):
    return network.graph.node[node]['netkit_host']

def netkit_hostname(network, node):
    #TODO: read host config from Config module
    return netkit_hosts()[netkit_host(network, node)]

def netkit_hosts():
    # Return all netkit hosts 
    # eg {1: 'trc1', 2: 'sknight'} etc
    return {1: 'netkithost'}


