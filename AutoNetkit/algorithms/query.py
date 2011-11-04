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

class Query(object):

    def __init__(self, network):
        self.network = network
#Setup query here
        attribute = Word(alphanums)
        condition = oneOf("< lt <= le == is eq >= ge > gt")
        value = Word(alphanums)
        query_element = Group(attribute("attribute") + condition("condition") + value("value")).setResultsName("query_element")
        booleans = oneOf("and && or || not !")
#TODO: Add support for parentheses
        self.query_parse = Group(query_element + ZeroOrMore(booleans + query_element)).setResultsName("Query")
        return
        
    def query(self, qstring):
        """ Query network property/properties
        """
        print "CALLED"
        print qstring
        result = self.query_parse.parseString(qstring)
        print "----------"
        print result.dump()
        print "----------"
        print G.nodes(data=True)
        return


G = nx.Graph()
Q = Query(G)
Q.query("A > 4 and B == 5 || c is AA")
