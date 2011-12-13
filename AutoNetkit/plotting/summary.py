# -*- coding: utf-8 -*-
"""
Summary of network
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['summarydoc']

import networkx as nx
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

# Network wide stats
    network_stats = {}
    network_stats['node_count'] = network.graph.number_of_nodes()
    network_stats['edge_count'] = network.graph.number_of_edges()
    as_graphs = ank.get_as_graphs(network)
    network_stats['as_count'] = len(as_graphs)

    as_stats = {}

    for single_as in as_graphs:
        print single_as.nodes(data=True)
# Get ASN of first node
        asn = network.asn(single_as.nodes()[0])
        print asn
        asn_nodes = []
        for node, data in single_as.nodes(data=True):
            pass

    


    # put html file in main plot directory
    html_filename = os.path.join(ank_main_dir, "summary.html")
    print html_filename
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render(
                network_stats = network_stats,
                    )
                    )


