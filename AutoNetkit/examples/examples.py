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

    >>> sorted(network.graph.nodes())
    [1a.AS1, 1b.AS1, 1c.AS1, 1d.AS1]

    >>> sorted(network.graph.edges())
    [(1a.AS1, 1b.AS1), (1b.AS1, 1a.AS1), (1b.AS1, 1c.AS1), (1b.AS1, 1d.AS1), (1c.AS1, 1b.AS1), (1c.AS1, 1d.AS1), (1d.AS1, 1b.AS1), (1d.AS1, 1c.AS1)]
    

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

    >>> sorted(network.graph.nodes())
    [1a.AS1, 1b.AS1, 1c.AS1, 2a.AS2, 2b.AS2, 2c.AS2, 2d.AS2, 3a.AS3]

    >>> sorted(network.graph.edges())
    [(1a.AS1, 1b.AS1), (1a.AS1, 1c.AS1), (1b.AS1, 1a.AS1), (1b.AS1, 1c.AS1), (1b.AS1, 3a.AS3), (1c.AS1, 1a.AS1), (1c.AS1, 1b.AS1), (1c.AS1, 2a.AS2), (2a.AS2, 1c.AS1), (2a.AS2, 2b.AS2), (2a.AS2, 2d.AS2), (2b.AS2, 2a.AS2), (2b.AS2, 2c.AS2), (2c.AS2, 2b.AS2), (2c.AS2, 2d.AS2), (2d.AS2, 2a.AS2), (2d.AS2, 2c.AS2), (2d.AS2, 3a.AS3), (3a.AS3, 1b.AS1), (3a.AS3, 2d.AS2)]

       
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



