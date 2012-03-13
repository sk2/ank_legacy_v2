# -*- coding: utf-8 -*-
"""
Summary of network
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['summarydoc']

import networkx as nx
import time
import AutoNetkit as ank
import logging
import os

from mako.lookup import TemplateLookup

# TODO: merge these imports but make consistent across compilers
from pkg_resources import resource_filename

#import network as network

LOG = logging.getLogger("ANK")

import shutil

import AutoNetkit as ank
from AutoNetkit import config
import itertools

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Check can write to template cache directory
#TODO: make function to provide cache directory
#TODO: move this into config
template_cache_dir = config.template_cache_dir

template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )


from AutoNetkit import config
settings = config.settings

LOG = logging.getLogger("ANK")

#TODO: add option to show plots, or save them


def summarydoc(network):
    """ Plot the network """
    ank_main_dir = config.ank_main_dir

    html_template = lookup.get_template("autonetkit/summary_html.mako")
    ank_css_template = lookup.get_template("autonetkit/style_css.mako")
    
    ebgp_graph = ank.get_ebgp_graph(network)
    ibgp_graph = ank.get_ibgp_graph(network)

# Network wide stats
    network_stats = {}
    network_stats['device_count'] = len(list(network.devices()))
    network_stats['router_count'] = len(list(network.routers()))
    network_stats['server_count'] = len(list(network.servers()))
    network_stats['edge_count'] = network.graph.number_of_edges()
    as_graphs = ank.get_as_graphs(network)
    network_stats['as_count'] = len(as_graphs)

    as_stats = {}

    for my_as in as_graphs:
        #print single_as.nodes(data=True)
# Get ASN of first node
        asn = my_as.asn
        #print asn
        node_list = {}
        loopbacks = []
        virtual_nodes = {}
        for router in network.routers(asn):
            node_label = network.fqdn(router)
            loopbacks.append( (node_label, network.lo_ip(router).ip))
            node_list[node_label] = {}
            interface_list = []
            ibgp_list = []
            ebgp_list = []
            for _, dst, data in network.graph.edges(router, data=True):
                interface_list.append( (ank.fqdn(network, dst), data['sn']))
            node_list[node_label]['interface_list'] = interface_list
            for _, dst, data in ebgp_graph.edges(router, data=True):
                ebgp_list.append( (ank.fqdn(network, dst), network.lo_ip(dst).ip))
            node_list[node_label]['ebgp_list'] = ebgp_list
            for _, dst, data in ibgp_graph.edges(router, data=True):
                ibgp_list.append( (ank.fqdn(network, dst), network.lo_ip(dst).ip))
            node_list[node_label]['ibgp_list'] = ibgp_list

        for virtual_node in network.virtual_nodes(asn):
            links = []
            for link in network.links(virtual_node):
                links.append( (link.local_ip, link.remote_ip, link.dst))
            virtual_nodes[virtual_node] = {
                'links': links,
                }

        as_stats[my_as.name] = {
                'asn': asn,
                'loopbacks': loopbacks,
                'node_list': node_list,
                'virtual_nodes': virtual_nodes,
                }

    plot_dir = config.plot_dir
    if not os.path.isdir(plot_dir):
        os.mkdir(plot_dir)

    timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
    
    css_filename = os.path.join(plot_dir, "ank_style.css")
    with open( css_filename, 'w') as f_css:
            f_css.write( ank_css_template.render())

    # put html file in main plot directory
    html_filename = os.path.join(plot_dir, "summary.html")
    #print html_filename
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render(
                network_stats = network_stats,
                as_stats = as_stats,
                timestamp=timestamp,
                css_filename = "./ank_style.css",
                    )
                    )


