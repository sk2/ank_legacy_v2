# -*- coding: utf-8 -*-
"""
Plotting
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['jsplot']

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


def jsplot(network):
    """ Plot the network """
    plot_dir = config.plot_dir
    if not os.path.isdir(plot_dir):
        os.mkdir(plot_dir)
    jsplot_dir = os.path.join(plot_dir, "jsplot")
    if not os.path.isdir(jsplot_dir):
        os.mkdir(jsplot_dir)

    js_template = lookup.get_template("arborjs/main_js.mako")
    css_template = lookup.get_template("arborjs/style_css.mako")
    html_template = lookup.get_template("arborjs/index_html.mako")
    ank_css_template = lookup.get_template("autonetkit/style_css.mako")

    node_list = []
    edge_list = network.graph.edges(data=True)
    for node in network.graph.nodes():
# Set label to be FQDN, so don't have multiple "Router A" nodes etc
        data = { 'label': "%s %s" % (ank.fqdn(network, node), network.lo_ip(node).ip)}
        node_list.append( (node, data))

    js_files = []
    timestamp = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())

    js_filename = os.path.join(jsplot_dir, "main.js")
    js_files.append("main.js")
    with open( js_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = node_list,
                edge_list = edge_list,
                physical_graph = True,
                ))
    
    #TODO: work out how to do multiple on one page
    ebgp_graph = ank.get_ebgp_graph(network)
    labels = dict( (n, network.label(n)) for n in ebgp_graph)
    ebgp_graph = nx.relabel_nodes(ebgp_graph, labels)
    ebgp_filename = os.path.join(jsplot_dir, "ebgp.js")
    js_files.append("ebgp.js")
    with open( ebgp_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = ebgp_graph.nodes(data=True),
                edge_list = ebgp_graph.edges(data=True),
                overlay_graph = True,
                ))

    ibgp_graph = ank.get_ibgp_graph(network)
    labels = dict( (n, network.label(n)) for n in ibgp_graph)
    ibgp_graph = nx.relabel_nodes(ibgp_graph, labels)
    ibgp_filename = os.path.join(jsplot_dir, "ibgp.js")
    js_files.append("ibgp.js")
    with open( ibgp_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = ibgp_graph.nodes(data=True),
                edge_list = ibgp_graph.edges(data=True),
                overlay_graph = True,
                ))

    #TODO: clarify difference of physical_graph and overlay_graph

    dns_graph = ank.get_dns_graph(network)
    node_list = []
    for node in dns_graph.nodes():
# Set label to be FQDN, so don't have multiple "Router A" nodes etc
        try:
            label = ank.fqdn(network, node)
        except KeyError:
            label = node
        data = { 'label': "%s (%s)" % (label, dns_graph.node[node].get("level"))}
        node_list.append( (node, data))
    dns_filename = os.path.join(jsplot_dir, "dns.js")
    js_files.append("dns.js")
    with open( dns_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = node_list,
                edge_list = dns_graph.edges(data=True),
                physical_graph = True,
                ))

    #TODO: add timestamps to plots
    # put html file in main plot directory
#TODO: parameterised/variable the css location
    html_filename = os.path.join(plot_dir, "plot.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "main.js",
                timestamp=timestamp,
                title = "network",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "ibgp.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "ibgp.js",
                timestamp=timestamp,
                title = "iBGP",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "ebgp.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "ebgp.js",
                timestamp=timestamp,
                title = "eBGP",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "dns.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "dns.js",
                timestamp=timestamp,
                title = "DNS",
                css_filename = "./ank_style.css",))

    css_filename = os.path.join(jsplot_dir, "style.css")
    with open( css_filename, 'w') as f_css:
            f_css.write( css_template.render())

    # and ank css_template
    css_filename = os.path.join(plot_dir, "ank_style.css")
    with open( css_filename, 'w') as f_css:
            f_css.write( ank_css_template.render())

    arbor_js_src_filename = os.path.join(template_dir, "arborjs", "arbor.js")
    arbor_js_dst_filename = os.path.join(jsplot_dir, "arbor.js")
    shutil.copy(arbor_js_src_filename, arbor_js_dst_filename)

