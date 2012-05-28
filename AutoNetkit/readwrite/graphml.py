# -*- coding: utf-8 -*-
"""
Graphml
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['load_graphml']

import networkx as nx
import itertools
import pprint
import AutoNetkit as ank
import os

#TODO: make work with network object not self.ank
#TODO: split into smaller (not exported) functions
import logging
LOG = logging.getLogger("ANK")

config = ank.config
settings = config.settings

def load_graphml(net_file, default_asn = 1):
    """
    Loads a network from Graphml into AutoNetkit.
    """
    default_device_type = 'router'
    path, filename = os.path.split(net_file)
    net_name = os.path.splitext(filename)[0]
    # get full path
    path =  os.path.abspath(path)
    pickle_dir = path + os.sep + "cache"
    if not os.path.isdir(pickle_dir):
        #os.mkdir(pickle_dir)
        pass
    pickle_file = "{0}/{1}.pickle".format(pickle_dir, net_name)
#TODO: re-enable pickle
    if (False and os.path.isfile(pickle_file) and
        os.stat(net_file).st_mtime < os.stat(pickle_file).st_mtime):
        # Pickle file exists, and source_file is older
        input_graph = nx.read_gpickle(pickle_file)
    else:
        # No pickle file, or is outdated
        input_graph = nx.read_graphml(net_file)
        #nx.write_gpickle(input_graph, pickle_file)

    nodes_with_H_set = sum(1 for n in input_graph if input_graph.node[n].get('H'))
    if nodes_with_H_set == len(input_graph):
#all nodes have H set, apply graph products
        LOG.info("All nodes in graph %s have H attribute set, applying graph product" % net_name)
        input_graph = ank.graph_product(net_file)
        if not input_graph:
            LOG.warn("Unable to load graph %s" % net_file)
            return
# remap ('a', 2) -> 'a2'
        nx.relabel_nodes(input_graph, 
                dict( (n, "%s_%s" % (n[0], n[1])) for n in input_graph), copy=False)
    
    try:
        if 'ASN' in input_graph.graph.get("node_default"):
            LOG.warn("Graph has ASN attribute set: did you mean 'asn'?")
    except TypeError:
        pass

    try:
        if input_graph.graph['node_default']['asn'] != "None":
            default_asn = int(input_graph.graph['node_default']['asn'])
    except KeyError:
        pass    # not set
    except ValueError:
        LOG.warn("Unable to use default asn '%s' specified in graphml file. Using %s instead." % (
            input_graph.graph['node_default']['asn'], default_asn))

# a->z for renaming
# try intially for a, b, c, d
    letters = (chr(x) for x in range(97,123)) 

# set any blank labels to be letter for gh-122
    no_label_nodes = [n for n, d in input_graph.nodes(data=True) if not d.get("label")]
    whitespace_labels = [n for n, d in input_graph.nodes(data=True)
            if n not in no_label_nodes and d.get("label").strip() == ""]
    empty_label_nodes = no_label_nodes + whitespace_labels
    if len(empty_label_nodes) > 26:
# use aa, ab, ac, etc
        single_letters = list(letters)
        letters = ("%s%s" % (a, b) for a in single_letters for b in single_letters)
# remove lowercase labels already used - conflicts in file naming
    existing_labels = set(data["label"].lower() for node, data in input_graph.nodes(data=True)
            if data.get("label"))
    letters = iter(set(letters) - existing_labels)

    mapping = dict( (n, letters.next()) for n in empty_label_nodes)
    input_graph = nx.relabel_nodes(input_graph, mapping)
# Update the label also
    for n in whitespace_labels:
        remapped_id = mapping[n] # need to refer to ID after mapping
        input_graph.node[remapped_id]['label'] = remapped_id



    # search for virtual nodes
    virtual_nodes = set(n for n, d in input_graph.nodes(data=True) if d.get("virtual"))
    for node in virtual_nodes:
        input_graph.node[node]['device_type'] = "virtual" 

    non_virtual_nodes = [n for n in input_graph if n not in virtual_nodes]
    for n in non_virtual_nodes:
        input_graph.node[n]['virtual'] = False
    

    # set node and edge defaults
    try:
        for node, data in input_graph.nodes(data=True):
            for key, val in input_graph.graph["node_default"].items():
                if key not in data and val != 'None':
                    data[key] = val
            input_graph.node[node] = data
    except KeyError:
        pass

    try:
        for s, t, data in input_graph.edges(data=True):
            for key, val in input_graph.graph["edge_default"].items():
                if key not in data and val != 'None':
                    data[key] = val
            input_graph[s][t] = data
    except KeyError:
        pass

    # set label if unset
    for node, data in input_graph.nodes(data=True):
        if 'label' not in data:
            input_graph.node[node]['label'] = node
        if 'device_type' not in data:
            input_graph.node[node]['device_type'] = default_device_type 
            LOG.debug("Setting device_type for %s to %s" % ( 
                input_graph.node[node]['label'], default_device_type) )

    # check each node has an ASN allocated
    for node, data in input_graph.nodes_iter(data=True):
        if not 'asn' in data:
            LOG.debug("No asn set for node %s using default of %s" % 
                     (data['label'],
                      default_asn))
            input_graph.node[node]['asn'] = default_asn
        else:
            input_graph.node[node]['asn'] = int(data['asn']) # ensure is integer

    # Convert to single-edge and then back to directed, to ensure edge in both
    # directions
    #TODO: Document this that assume bi-directional

    input_graph = nx.Graph(input_graph)
    input_graph = input_graph.to_directed()
    
    return input_graph
