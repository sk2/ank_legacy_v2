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
#TODO: tidy these up with the embedded network in node name

    node_list = ( (node.fqdn, {'label': network.fqdn(node)}) for node in network.graph.nodes())
    edge_list = list( (src.fqdn, dst.fqdn, {}) 
            for (src, dst, data) in network.graph.edges(data=True))


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

    js_filename = os.path.join(jsplot_dir, "ip.js")
    js_files.append("ip.js")
    node_list = []
    for node in network.graph.nodes():
# Set label to be FQDN, so don't have multiple "Router A" nodes etc
        data = { 'label': "%s %s" % (ank.fqdn(network, node), network.lo_ip(node).ip)}
        node_list.append( (node.fqdn, data))
    edge_list = list( (src.fqdn, dst.fqdn, data['sn']) 
            for (src, dst, data) in network.graph.edges(data=True))
    with open( js_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = node_list,
                edge_list = edge_list,
                physical_graph = True,
                ))

    js_filename = os.path.join(jsplot_dir, "igp.js")
    js_files.append("igp.js")
    node_list = []
    for node in network.graph.nodes():
        if not node.igp_link_count:
# no IGP links, don't add to plot
            continue
# Set label to be FQDN, so don't have multiple "Router A" nodes etc
        data = { 'label': "%s" % node.fqdn}
        node_list.append( (node.fqdn, data))
    edge_list = list( (src.fqdn, dst.fqdn, data.get('weight')) 
            for (src, dst, data) in network.graph.edges(data=True)
            if src.asn == dst.asn)
    with open( js_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = node_list,
                edge_list = edge_list,
                physical_graph = True,
                ))
    
    #TODO: work out how to do multiple on one page
    ebgp_graph = ank.get_ebgp_graph(network)
    labels = dict( (n, network.label(n)) for n in ebgp_graph)
    nx.relabel_nodes(ebgp_graph, labels, copy=False)
    ebgp_filename = os.path.join(jsplot_dir, "ebgp.js")
    js_files.append("ebgp.js")
    with open( ebgp_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = ebgp_graph.nodes(data=True),
                edge_list = ebgp_graph.edges(data=True),
                overlay_graph = True,
                ))

    ibgp_graph = ank.get_ibgp_graph(network)
    node_list = []
    for node in ibgp_graph.nodes():
# Set label to be FQDN, so don't have multiple "Router A" nodes etc
        data = { 'label': "%s (%s)" % (node.fqdn, network.graph.node[node].get("ibgp_level"))}
        node_list.append( (node.fqdn, data))
    edge_list = ibgp_graph.edges(data=True)
    edge_list = list( (src.fqdn, dst.fqdn, data.get("rr_dir")) for (src, dst, data) in edge_list)

    ibgp_filename = os.path.join(jsplot_dir, "ibgp.js")
    js_files.append("ibgp.js")
    with open( ibgp_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = node_list,
                edge_list = edge_list,
                physical_graph = True,
                ))

    #TODO: clarify difference of physical_graph and overlay_graph

#TODO: see if js_files ever used

    dns_graph = ank.get_dns_graph(network)
    node_list = []
    for node in dns_graph.nodes():
# Set label to be FQDN, so don't have multiple "Router A" nodes etc
        data = { 'label': "%s (%s)" % (node.fqdn, dns_graph.node[node].get("level"))}
        node_list.append( (node.fqdn, data))
    dns_filename = os.path.join(jsplot_dir, "dns.js")
    edge_list = dns_graph.edges(data=True)
    #edge_list = list( (src.fqdn, dst.fqdn, data.get('dns_dir')) for (src, dst, data) in edge_list)
    edge_list = list( (src.fqdn, dst.fqdn, '') for (src, dst, data) in edge_list)
    js_files.append("dns.js")
    with open( dns_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = node_list,
                edge_list = edge_list,
                physical_graph = True,
                ))


    dns_auth_graph = ank.get_dns_auth_graph(network)
    node_list = []
    for node in dns_auth_graph.nodes():
# Set label to be FQDN, so don't have multiple "Router A" nodes etc
        data = { 'label': "%s" % node.label}
        node_list.append( (node.fqdn, data))
    dns_filename = os.path.join(jsplot_dir, "dns_auth.js")
    edge_list = dns_auth_graph.edges(data=True)
    edge_list = list( (src.fqdn, dst.fqdn, data) for (src, dst, data) in edge_list)
    js_files.append("dns_auth.js")
    with open( dns_filename, 'w') as f_js:
            f_js.write( js_template.render(
                node_list = node_list,
                edge_list = edge_list,
                physical_graph = True,
                ))

    #TODO: add timestamps to plots
    # put html file in main plot directory
#TODO: parameterised/variable the css location
    plot_width = config.settings['Plotting']['jsplot width']
    plot_height = config.settings['Plotting']['jsplot height']
    html_filename = os.path.join(plot_dir, "plot.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "main.js",
                timestamp=timestamp,
                plot_width = plot_width,
                plot_height = plot_height,
                title = "Physical Network",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "ip.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "ip.js",
                timestamp=timestamp,
                plot_width = plot_width,
                plot_height = plot_height,
                title = "IP",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "igp.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "igp.js",
                timestamp=timestamp,
                plot_width = plot_width,
                plot_height = plot_height,
                title = "IGP",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "ibgp.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "ibgp.js",
                timestamp=timestamp,
                plot_width = plot_width,
                plot_height = plot_height,
                title = "iBGP",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "ebgp.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "ebgp.js",
                timestamp=timestamp,
                plot_width = plot_width,
                plot_height = plot_height,
                title = "eBGP",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "dns.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "dns.js",
                timestamp=timestamp,
                plot_width = plot_width,
                plot_height = plot_height,
                title = "DNS Hierarchy",
                css_filename = "./ank_style.css",))

    html_filename = os.path.join(plot_dir, "dns_auth.html")
    with open( html_filename, 'w') as f_html:
            f_html.write( html_template.render( js_file = "dns_auth.js",
                timestamp=timestamp,
                plot_width = plot_width,
                plot_height = plot_height,
                title = "DNS Authority",
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

