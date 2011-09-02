# -*- coding: utf-8 -*-
"""
Plotting
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['plot']

import networkx as nx
import AutoNetkit as ank
import logging
LOG = logging.getLogger("ANK")


def plot(network):
    """ Plot the network """
    graph = network.graph
    pos = nx.spring_layout(graph)
    plot_graph(graph, title="Network", pos=pos)
    plot_bgp(network, pos=pos)
    plot_ibgp(network, pos=pos)


def plot_bgp(network, pos=None):
    graph = ank.get_ebgp_graph(network)
    labels = dict( (n, network.label(n)) for n in graph)
    plot_graph(graph, title="eBGP", pos=pos, labels=labels)

def plot_ibgp(network, pos=None):
    graph = ank.get_ibgp_graph(network)
    labels = dict( (n, network.label(n)) for n in graph)
    plot_graph(graph, title="iBGP", pos=pos, labels=labels)

def plot_graph(graph, title=None, filename=None, pos=None, labels=None):
    if graph.number_of_nodes() == 0:
        LOG.debug("{0} graph is empty, not plotting".format(title))

    if not pos:
        pos=nx.spring_layout(graph)

    # If none, filename based on title
    if not filename:
        filename = "{0}.pdf".format(title)
        # Remove any spaces etc from filename
        filename.replace(" ", "_")

    try:
        import matplotlib.pyplot as plt
    except:
        raise

    # Colors
    node_color = "#336699"
    font_color = "k"
    edge_color = "gray"
    title_color = "k"
    caption_color = 'gray'

    # Easier reference
    plt.clf()
    #TODO: make position take into account labels
    #pos = nx.spring_layout(graph, scale=0.1)
    cf = plt.gcf()
    ax=cf.add_axes((0,0,1,1))
    # Create axes to allow adding of text relative to map
    ax.set_axis_off() 

    nx.draw_networkx_nodes(graph, pos, 
                           node_size = 50, 
                           alpha = 0.8, linewidths = (0,0),
                           node_color = node_color)

    nx.draw_networkx_edges(graph, pos, arrows=False,
                           edge_color=edge_color,
                           alpha=0.8)

    if not labels:
        labels = {}
        for n, data in graph.nodes(data = True):
            label = data.get('label')
            if title == 'Network' and 'lo_ip' in data:
                label += "\n%s" % data['lo_ip']
            labels[n] = label 


    #TODO: mark eBGP links, and iBGP routers, DNS servers, etc 

    nx.draw_networkx_labels(graph, pos, 
                            labels=labels,
                            font_size = 8,
                            font_color = font_color)

    plt.title("test")

    ax.text(0.02, 0.98, title, horizontalalignment='left',
                            weight='heavy', fontsize=16, color=title_color,
                            verticalalignment='top', 
                            )
                            #transform=ax.transAxes)

    plt.show()
    plt.savefig(filename)

    #plt.savefig( filename, format = 'pdf',
    #            bbox_inches='tight',
    #            facecolor = "w", dpi = 300,
    #            pad_inches=0.1,
    #           )

    plt.close()


