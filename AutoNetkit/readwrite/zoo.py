# -*- coding: utf-8 -*-
"""
Zoo
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['load_zoo']

import networkx as nx
import AutoNetkit as ank
import os

from collections import defaultdict

#TODO: make work with network object not self.ank
#TODO: split into smaller (not exported) functions
import logging
LOG = logging.getLogger("ANK")

config = ank.config
settings = config.settings

def load_graph(net_file):
    """ Loads net_file. If present in cache and not out of data,
    cached copy will be used, otherwise file loaded with a copy stored in cache.
    Cache is a pickle file, avoids having to run parser across GML file each
    time"""
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
        graph = nx.read_gpickle(pickle_file)
    else:
        # No pickle file, or is outdated
        graph = nx.read_gml(net_file)
        nx.write_gpickle(graph, pickle_file)
    # ANK only understands GML files cleaned by topzootools
    if 'Creator' in graph.graph:
        if graph.graph['Creator'] == "Topology Zoo Toolset":
            # Graph has been processed by topzootools into suitable 
            # format for ank
            return graph
        elif graph.graph['Creator'] == ' "yFiles"':
            # Note yFiles has quotes and leading space after nx parsing
            #TODO: try and use topzootools module (if installed)
            # to do conversion
            # to a /tmp file
            LOG.warn("Using GML file exported from yED, "
                    "Please use TopZooTools to convert yED GML file"
                    " into Topology Zoo format for use in AutoNetkit")
            #TODO: make this throw exception so that program exits
            return None
        else:
            #Unknown file creator, may be user manually created, but warn
            LOG.warn("Unknown GML file creator")
            return graph
    else:
        # No creator specified
        return graph
            

def load_zoo(network, net_file):
    """
    Loads a network from the zoo into AutoNetkit.
    If the file is interconnect.gml, it will treat the "type" of each node as
    the source filename of a network to load. This can be used to construct
    graphs of Multiple ASes.
    """

    #TODO: combine with current graph as final step, see if netx
    # will auto renumber nodes if necessary, to allow multiple ASes to be
    # loaded and combined

    #TODO: allow support for loading interconnect file
    #TODO: allow support for loading multiple zoo files, inc node
    #renumbering if necessary
    #TODO: set speeds based on linkspeed edge attribute from zoo, with
    # default speed if none set
    input_graph = load_graph(net_file)
    if not input_graph:
        # Nothing to process
        return

    # See if normal zoo graph of interconnect graph
    interconnect_graph = None
    # Graphs in the network to process
    if ('label' in input_graph.graph and
        input_graph.graph['label'] == 'interconnect'):
        network_graphs = []
        # Map filenames (used in interconnect graph) to
        # network names (used in ank), so can connect the networks
        network_graph_names = {}
        interconnect_graph = input_graph
        networks_to_load = [data['type'] for n, data in
                            interconnect_graph.nodes(data=True)]
        # Remove duplicates
        networks_to_load = list(set(networks_to_load))
        # Get location of zoo networks from config
        #TODO: document this config setting
        #zoo_dir = settings.get('Zoo', 'zoo_dir')
        # Assume files in same directory as interconnect file
        zoo_dir = os.path.split(net_file)[0]
        # Now look for the files in the zoo dir
        for net_load_file in networks_to_load:
            full_path = "{0}/{1}".format(zoo_dir, net_load_file)
            if os.path.exists(full_path):
                # load the network
                graph = load_graph(full_path)
                # Get the name of the network, to use when interconnecting
                network_graph_names[net_load_file] = graph.graph['Network']
                network_graphs.append(graph)
            else:
                LOG.warn("Unable to find {0} in {1}".format(net_load_file,
                                                            zoo_dir))
        for graph in network_graphs:
            #TODO: dont load external graphs for interconnect
            graph = graph_to_ank(network, graph, include_ext_nodes = False)
            network.graph = nx.disjoint_union(network.graph, graph)
    else:
        # TODO: clean this up
        if ('Network' in input_graph.graph 
            and input_graph.graph['Network'] == "European NRENs"):
            # For Infocom Paper
            # Use graph directly
            network.graph = input_graph.to_directed()
            # Store the AS names
            as_names = dict( set( (int(data['asn']), data['Network']) for
                                 node, data in
                                 input_graph.nodes_iter(data=True)))
            network.as_names.update(as_names)

            # And allocate AS graph
            # ANK uses directed graphs
        else:
            # convert as appropriate
            network.graph = graph_to_ank(network, input_graph)

    def ank_node_from_inter(data):
        #TODO: generalise the last section
        # Network specified as a file, get the network name for this node
        filename = data['type']
        if filename in network_graph_names:
            network_name = network_graph_names[filename]
            # and convert to asn
            asn = None
            #TODO: look for cleaner way to search dict items
            for curr_asn, curr_asn_name in network.as_names.items():
                if curr_asn_name == network_name:
                    asn = int(curr_asn)
                    if not asn:
                        LOG.warn("Unable to find ASN for network "
                                 "{0}".format(network_name))
                        return
                label = data['label']
                # Now find the node that has this asn and label
                for node, data in network.graph.nodes(data=True):
                    if data['label'] == label and data['asn'] == asn:
                        return node
            else:
                # Probably didn't load the network correctly
                # TODO: throw error
                pass

    if interconnect_graph:
        # Connect the networks together
        add_edge_list = []
        for src, dst in interconnect_graph.edges():
            # Need to find the src and dst nodes in the ank network
            src_ank = ank_node_from_inter(interconnect_graph.node[src])
            dst_ank = ank_node_from_inter(interconnect_graph.node[dst])
            if src_ank != None and dst_ank != None:
                # And connect these two nodes in the main graph
                #TODO: apply any appropriate BGP policy from interconnect_graph
                add_edge_list.append((src_ank, dst_ank))
                add_edge_list.append((dst_ank, src_ank))
        network.graph.add_edges_from(add_edge_list)
    #TODO: make this only apply to graph nodes for newly added graph not
    #globally to whole network
    network.set_default_node_property('platform', "NETKIT")


def graph_to_ank(network, graph, asn=None, include_ext_nodes=True):
    """ Converts a GML graph from the Zoo into AutoNetkit compatible graph"""
    # Default label
    if not 'Network' in graph.graph:
        graph.graph['Network'] = "Network"

    # if no asn set, use next available
    #TODO: put this into a function which returns a graph for combining at the
    # end
    LOG.debug("passed in asn of %s " % asn)
    if graph.is_multigraph():
        graph = nx.DiGraph(graph)
        if 'Network' in graph.graph:
            LOG.info(("Converting {0} to single-edge graph").format(
                graph.graph['Network']))
        else:
            LOG.info("Converting to single-edge graph")
    # ANK uses directed graphs
    graph = graph.to_directed()
    #TODO: see if ASN set in the graph
    asn_list = ank.nodes_by_as(network).keys()

    LOG.debug("current ASN list %s " % asn_list)

    # And append any ASNs manually specified
    manual_asn = {}
    for node, data in graph.nodes(data=True):
        if ('type' in data and data['type'].startswith("AS") and
            data['type'][2:].isdigit()):
            # This node has a valid manually specified ASN
            node_asn = int(data['type'][2:])
            manual_asn[node] = node_asn

    # Unique
    manual_asn_unique = list(set(manual_asn.keys()))
    for node_asn in manual_asn_unique:
        if node_asn in asn_list:
            LOG.warn("Manually specified ASN %i already in use" % asn)
    # Record these as in use
    asn_list += manual_asn_unique
    LOG.debug("asn list after adding manual uniques %s " % asn_list)

    # Allocate asns
    # Find next free asn
    def next_unallocated_asn():
        LOG.debug("nua fn asn list %s " % asn_list)
        if len(asn_list) > 0:
            nua = max(asn_list)
            while nua in asn_list:
                try:
                    nua += 1
                except TypeError as e:
                    LOG.warn("Unable to set Next Unallocated ASN %i to ASN list"
                             " %s " % (nua, asn_list))

                asn_list.append(nua)
                return nua
        else:
            # No asn in use
            nua = 1
            asn_list.append(nua)
            return nua

    #TODO: clean up this logic
    if asn and asn in asn_list:
        # User specified asn already in use
        LOG.warn("ASN %s already in use" % asn)
    elif asn:
        # Record as being used
        asn_list.append(int(asn))
        # Record name for DNS
        network.as_names[asn] = graph.graph['Network']
    else:
        # No asn set, use next available
        asn = next_unallocated_asn()
        # and record
        network.as_names[asn] = graph.graph['Network']

    #TODO: check that writing using names doesn't overwrite the  same folder
    # eg may have 5 AARNET nodes, but all overwrite same folder in nk lab
    # If multiple external nodes with same name, merge into single node
    # TODO: make this behaviour able to be turned on/off
    # eg either merge, keep, make unique, or remove, depending on how
    # external names combined
    #TODO: use include_external_nodes
    external_nodes = [node for node in graph.nodes()
                        if ('Internal' in
                            graph.node[node] and
                            graph.node[node]['Internal'] == 0)]
    # Group external nodes by their name
    ext_node_dict = defaultdict(list)
    for node in external_nodes:
        if not include_ext_nodes:
            graph.remove_node(node)
        else:
            label = graph.node[node]['label']
            ext_node_dict[label].append(node)
            # Now merge nodes
            for label, nodes in ext_node_dict.items():
                if len(nodes) > 1:
                    # Multiple nodes for this label, merge
                    # Choose the first (arbitary) node to merge others into
                    primary_node = nodes.pop()
                    for node in nodes:
                        # merge remaining nodes into primary node
                        # get edges from this node
                        #TODO: look at using edges_iter here
                        for src, dst, data in graph.edges(node,
                                                          data=True):
                            # add link from primary
                            graph.add_edge(primary_node, dst, data)
                            # and reverse link
                            graph.add_edge(dst, primary_node, data)
                            graph.remove_node(node)

    for node in graph:
        if node in manual_asn:
            # Node has ASN manually specified (as previously determined)
            graph.node[node]['asn'] = manual_asn[node]
        elif ('Internal' in graph.node[node]):
            if graph.node[node]['Internal'] == 1:
                graph.node[node]['asn'] = asn
            elif graph.node[node]['Internal'] == 0:
                graph.node[node]['asn'] = next_unallocated_asn()
        else:
            # No internal/external set, assume all internal nodes
            graph.node[node]['asn'] = asn

    # Check labels are unique
    # Store nodes by their label, duplicates are labels with more than one node
    nodes_by_label = defaultdict(list)
    all_labels = set()
    for node, data in graph.nodes_iter(data=True):
        nodes_by_label[data['label']].append(node)
        all_labels.add(data['label'])
    duplicates = ( (label, nodes) for (label, nodes) in nodes_by_label.items()
                  if len(nodes) > 1)
    for (label, nodes) in duplicates:
        if label == '':
            label = "Untitled"
        for index, node in enumerate(nodes):
            node_label = "%s_%s" % (label, index)
            if node_label in all_labels:
                # TODO: throw error
                print "Node label %s already used " % node_label
            else:
                all_labels.add(node_label)
                graph.node[node]['label'] = node_label
            #TODO: log to debug the changed label name

    #TODO: check no blank labels
    #TODO: put this into general algorithms module
       #TODO: replace with helper methods to return fqdn and folder names
    return graph


