# -*- coding: utf-8 -*-
"""
Implement graph products

"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen, Eric Parsonage

import networkx as nx
import logging
import itertools

LOG = logging.getLogger("ANK")

__all__ = ['graph_product']


def graph_product(G, H_graphs):
    """
    >>> G = nx.Graph([(1,2, dict(operator = 'cartesian')), (1,3, dict(operator = 'cartesian')),  (2,3, dict(operator = 'cartesian'))])
    >>> G.add_nodes_from([ (1, dict(H='style_a')), (2, dict(H='style_a')), (3, dict(H='style_a'))])
    >>> H_graphs = {}
    >>> H_graphs['style_a'] = nx.Graph( [('a','b')])
    >>> H_graphs['style_b'] = nx.Graph( [('a','b'), ('a','c')])


    """

