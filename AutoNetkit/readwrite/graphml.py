# -*- coding: utf-8 -*-
"""
Graphml
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['load_graphml']

import networkx as nx
import AutoNetkit as ank
import os

#TODO: make work with network object not self.ank
#TODO: split into smaller (not exported) functions
import logging
LOG = logging.getLogger("ANK")

config = ank.config
settings = config.settings

def load_graphml(network, net_file, default_asn = 1):
    """
    Loads a network from Graphml into AutoNetkit.
    """
    path, filename = os.path.split(net_file)
    net_name = os.path.splitext(filename)[0]
    # get full path
    path =  os.path.abspath(path)
    pickle_dir = path + os.sep + "cache"
    if not os.path.isdir(pickle_dir):
        os.mkdir(pickle_dir)
    pickle_file = "{0}/{1}.pickle".format(pickle_dir, net_name)
    if (os.path.isfile(pickle_file) and
        os.stat(net_file).st_mtime < os.stat(pickle_file).st_mtime):
        # Pickle file exists, and source_file is older
        input_graph = nx.read_gpickle(pickle_file)
    else:
        # No pickle file, or is outdated
        input_graph = nx.read_graphml(net_file)
        nx.write_gpickle(input_graph, pickle_file)

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

    # Convert to single-edge and then back to directed, to ensure edge in both
    # directions
    #TODO: Document this that assume bi-directional
    input_graph = nx.Graph(input_graph)
    network.graph = input_graph.to_directed()
    
    network.set_default_node_property('platform', "NETKIT")
    return

