# -*- coding: utf-8 -*-
"""
Graphml
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['load_pickle']

import networkx as nx
import AutoNetkit as ank

#TODO: make work with network object not self.ank
#TODO: split into smaller (not exported) functions
import logging
LOG = logging.getLogger("ANK")

config = ank.config
settings = config.settings

def load_pickle(net_file, default_asn = 1):
    """
    Loads a network from Graphml into AutoNetkit.
    """
    input_graph = nx.read_gpickle(net_file)

    # set label if unset
    for node in input_graph.nodes_iter():
        if 'label' not in input_graph.node[node]:
            input_graph.node[node]['label'] = node

    # check each node has an ASN allocated
    for node, data in input_graph.nodes_iter(data=True):
        if not 'asn' in data:
            LOG.info("No asn set for node %s using default of %s" % 
                     (data['label'],
                      default_asn))
            input_graph.node[node]['asn'] = default_asn
        else:
            input_graph.node[node]['asn'] = int(data['asn']) # ensure is integer

    # Convert to single-edge and then back to directed, to ensure edge in both
    # directions
    #TODO: Document this that assume bi-directional
    input_graph = nx.Graph(input_graph)
    input_graph.graph = input_graph.to_directed()
    
    input_graph.set_default_node_property('platform', "NETKIT")
    return input_graph

