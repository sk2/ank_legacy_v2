# -*- coding: utf-8 -*-
"""
Query
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

import networkx as nx
import AutoNetkit as ank
import logging
LOG = logging.getLogger("ANK")
#TODO: only import what is needed
from pyparsing import *
from booleano.parser import Grammar, ConvertibleParseManager





class Query(object):

    def __init__(self, network):
        self.network = network
#Setup query here
        new_tokens = {
                'not': "not",
                'eq': "is",
                'ne': "isn't",
                'belongs_to': "in",
                'and': 'and',
                'is_subset': "are included in",
                }
        grammar = Grammar(**new_tokens)
        self.parse_manager = ConvertibleParseManager(grammar)
        return
        
    def query(self, qstring):
        """ Query network property/properties
        """
        print self.parse_manager.parse(qstring)

        return


G = nx.Graph()
Q = Query(G)
Q.query('"thursday" in {"monday", "tuesday", "wednesday", "thursday", "friday"}')
Q.query('today is "2009-07-17"')
Q.query("a > 5 and b < 4")
#Q.query("A > 4 and B == 5 || c is AA")
#Q.query("A > 4 and B == 5")
