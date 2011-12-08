# -*- coding: utf-8 -*-
"""
Plotting
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['plot', 'plot_graph']

import networkx as nx
import AutoNetkit as ank
import logging
import os

from AutoNetkit import config
settings = config.settings

LOG = logging.getLogger("ANK")

#TODO: add option to show plots, or save them


def cmap_index(network, subgraph, attr='asn'):
    #TODO: see if more pythonic way to do this
# List of attributes
    attr_list = sorted(list(set(network.graph.node[n].get(attr) for n in subgraph)))
    return [attr_list.index(network.graph.node[n].get(attr)) for n in subgraph]

def plot(network, show=False, save=True):
    """ Plot the network """
    plot_dir = config.plot_dir
    if not os.path.isdir(plot_dir):
        os.mkdir(plot_dir)

    graph = network.graph
    pos = nx.spring_layout(graph)

# Different node color for each AS. Use heatmap based on ASN

    plot_graph(graph, title="Network", pos=pos, show=show, save=save,
            node_color=cmap_index(network, graph))

    graph = ank.get_ebgp_graph(network)
    labels = dict( (n, network.label(n)) for n in graph)
    plot_graph(graph, title="eBGP", pos=pos, labels=labels, show=show, save=save)

    graph = ank.get_ibgp_graph(network)
    labels = dict( (n, network.label(n)) for n in graph)
    plot_graph(graph, title="iBGP", pos=pos, labels=labels, show=show, save=save)
    
def plot_graph(graph, title=None, filename=None, pos=None, labels=None,
        node_color=None,
        show=False, save=True):
    if graph.number_of_nodes() == 0:
        LOG.debug("{0} graph is empty, not plotting".format(title))

    if show:
        # Larger plots for inline plotting
        from pylab import rcParams
        rcParams['figure.figsize'] = 20, 10

    if not pos:
        pos=nx.spring_layout(graph)

    # If none, filename based on title
    if not filename:
        plot_dir = config.plot_dir
        filename = plot_dir + os.sep + "%s.pdf" % title
        # Remove any spaces etc from filename
        filename.replace(" ", "_")

    try:
        import matplotlib.pyplot as plt
    except:
        print "Matplotlib not found, not plotting using Matplotlib"
        return

    # Colors
    if not node_color:
        node_color = "#336699"
    font_color = "k"
    edge_color = "#348ABD"
    title_color = "k"

    # Easier reference
    plt.clf()
    #TODO: make position take into account labels
    #pos = nx.spring_layout(graph, scale=0.1)
    cf = plt.gcf()
    ax=cf.add_axes((0,0,1,1))
    # Create axes to allow adding of text relative to map
    ax.set_axis_off() 

    nx.draw_networkx_nodes(graph, pos, 
                           node_size = 120, 
                           alpha = 0.8, linewidths = (0,0),
                           node_color = node_color,
                           cmap=plt.cm.jet)

    nx.draw_networkx_edges(graph, pos, arrows=False,
                           edge_color=edge_color,
                           alpha=0.8)

# Draw nodes that have pos for but not in graph for visual continuity
# so same scale, eg so eBGP graph has same positions
#TODO: find better way to scale and set axes directly
    g_non_plotted = nx.Graph()
    g_non_plotted.add_nodes_from(n for n in pos if n not in graph)
    nx.draw_networkx_nodes(g_non_plotted, pos, alpha =0, visible=False)

    if not labels:
        labels = {}
        for n, data in graph.nodes(data = True):
            label = "\n" + data.get('label')
            if title == 'Network' and 'lo_ip' in data:
                label += " (%s)" % data['lo_ip'].ip
            labels[n] = label 


    #TODO: mark eBGP links, and iBGP routers, DNS servers, etc 

    nx.draw_networkx_labels(graph, pos, 
                            labels=labels,
                            font_size = 12,
                            font_color = font_color)

    ax.text(0.02, 0.98, title, horizontalalignment='left',
                            weight='heavy', fontsize=16, color=title_color,
                            verticalalignment='top', 
                            transform=ax.transAxes)

    if show:
        plt.show()
    if save:
        plt.savefig(filename)

    #plt.savefig( filename, format = 'pdf',
    #            bbox_inches='tight',
    #            facecolor = "w", dpi = 300,
    #            pad_inches=0.1,
    #           )

    plt.close()


