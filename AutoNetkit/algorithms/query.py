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
import operator

graph = nx.read_gpickle("condensed_west_europe.pickle")
#print graph.nodes(data=True)

##### parser
# Node selection syntax

attribute = Word(alphas, alphanums+'_').setResultsName("attribute")
#TODO: check how evaluation examples on pyparsing work out which comparison/operator is used

lt = Literal("<").setResultsName("<")
le = Literal("<=").setResultsName("<=")
eq = Literal("=").setResultsName("=")
ne = Literal("!=").setResultsName("!=")
ge = Literal(">=").setResultsName(">=")
gt = Literal(">").setResultsName(">")

opn = {
        '<': operator.lt,
        '<=': operator.le,
        '=': operator.eq,
        '>=': operator.ge,
        '>': operator.gt,
        '&': operator.and_,
        '|': operator.or_,
        }

# Both are of comparison to access in same manner when evaluating
comparison = (lt | le | eq | ne | ge | gt).setResultsName("comparison")
stringComparison = (eq | ne).setResultsName("comparison")
#
#quoted string is already present
integer = Word(nums).setResultsName("value").setParseAction(lambda t: int(t[0]))

#TODO: allow parentheses? - should be ok as pass to the python parser

boolean_and = Literal("&").setResultsName("&")
boolean_or = Literal("|").setResultsName("|")
boolean = boolean_and | boolean_or

numericQuery = Group(attribute + comparison + integer)
stringQuery =  Group(attribute + stringComparison + quotedString.setResultsName("value"))

singleQuery = numericQuery("numericQuery") | stringQuery("stringQuery")
query = singleQuery + Optional(boolean + singleQuery)

tests = [
        #'A = "aaaaa"',
        #'A = "aaaaa aa"',
        #'A = 1',
        #'A = 1 & b = 2',
        #'A = 1 & b = "aaa"',
        #'Network = "ACOnet"',
        'asn = 680',
        ]


def evaluate(s):
    """ Evaluates the stack"""
    # baed on fourFn.py
    pass

for test in tests:
    print "--------------------------"
    print test
    result = query.parseString(test)
    print result.dump()
    print "----"
#TODO: function factories???
    def comp_fn_string(token):
        return opn[token.comparison](graph.node[n].get(token.attribute), token.value)

    def comp_fn_numeric(token):
        return opn[token.comparison](float(graph.node[n].get(token.attribute)), token.value)


    for key, token in result.items():
        if key == "numericQuery":
            comp_fn = comp_fn_numeric
        elif key == "stringQuery":
            comp_fn = comp_fn_string

# evalue
        result_set = [n for n in graph if comp_fn(token) ]
        print result_set




# can set parse action to be return string?

#TODO: create function from the parsed result
# eg a lambda, and then apply this function to the nodes in the graph
# eg G.node[n].get(attribute) = "quotedstring"  operator 
