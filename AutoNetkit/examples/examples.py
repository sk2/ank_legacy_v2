# -*- coding: utf-8 -*-
"""
Examples
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['example_single_as', 'example_multi_as']

#TODO: make these load the topology files directly?
#TODO: use sorted in examples to make easier to read

import AutoNetkit
import logging
import networkx as nx
LOG = logging.getLogger("ANK")


def example_single_as():
    """ Single AS example topology

    >>> network = example_single_as()

    >>> network.graph.nodes()
    ['1a', '1c', '1b', '1d']

    >>> network.graph.edges()
    [('1a', '1b'), ('1c', '1b'), ('1c', '1d'), ('1b', '1a'), ('1b', '1c'), ('1b', '1d'), ('1d', '1c'), ('1d', '1b')]
    

    """
    network = AutoNetkit.network.Network()
    graph = nx.Graph()
    graph.add_nodes_from( [
            ('1a', {'asn': 1}), ('1b', {'asn': 1}),
            ('1c', {'asn': 1}), ('1d', {'asn': 1})])

    graph.add_edges_from( [
            ('1a', '1b'), ('1b', '1c'),
            ('1c', '1d'), ('1d', '1b')])

    network.graph = graph.to_directed()
    network.instantiate_nodes()

    return network

def example_multi_as():
    """ Multi AS example topology

#TODO: update these with bi-directional edges

    >>> network = example_multi_as()

    >>> network.graph.nodes()
    ['1a', '2d', '1c', '1b', '2a', '2b', '2c', '3a']

    >>> network.graph.edges()
    [('1a', '1c'), ('1a', '1b'), ('2d', '3a'), ('2d', '2a'), ('2d', '2c'), ('1c', '1a'), ('1c', '1b'), ('1c', '2a'), ('1b', '1a'), ('1b', '1c'), ('1b', '3a'), ('2a', '2d'), ('2a', '1c'), ('2a', '2b'), ('2b', '2a'), ('2b', '2c'), ('2c', '2d'), ('2c', '2b'), ('3a', '2d'), ('3a', '1b')]
       
    """
    network = AutoNetkit.network.Network()
    graph = nx.Graph()
    graph.add_nodes_from( [
            ('1a', {'asn': 1}), ('1c', {'asn': 1}),
            ('1b', {'asn': 1}), ('2a', {'asn': 2}),
            ('2b', {'asn': 2}), ('2c', {'asn': 2}),
            ('2d', {'asn': 2}), ('3a', {'asn': 3})])

    graph.add_edges_from( [
            ('1a', '1b'), ('1a', '1c'),
            ('1b', '1c'), ('2a', '2b'),
            ('2b', '2c'), ('2c', '2d'),
            ('2d', '2a'), ('1c', '2a'),
            ('2d', '3a'), ('3a', '1b')])

    network.graph = graph.to_directed()
    network.instantiate_nodes()

    return network



