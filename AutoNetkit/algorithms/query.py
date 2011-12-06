# -*- coding: utf-8 -*-
"""
Query
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

import networkx as nx
import logging
LOG = logging.getLogger("ANK")
#TODO: only import what is needed
from pyparsing import *
import operator
import os
import pprint
import itertools
import TopZooTools
import TopZooTools.geoplot


#TODO: apply stringEnd to the matching parse queries to ensure have parsed all

graph = nx.read_gpickle("condensed_west_europe.pickle")
#print graph.nodes(data=True)

##### parser
# Node selection syntax

attribute = Word(alphas, alphanums+'_').setResultsName("attribute")
#TODO: check how evaluation examples on pyparsing work out which comparison/operator is used


#TODO: allow wildcards

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
        '&': set.intersection,
        '|': set.union,
        }

# Both are of comparison to access in same manner when evaluating
comparison = (lt | le | eq | ne | ge | gt).setResultsName("comparison")
stringComparison = (eq | ne).setResultsName("comparison")
#
#quoted string is already present
float_string = Word(nums).setResultsName("value").setParseAction(lambda t: float(t[0]))
integer_string = Word(nums).setResultsName("value").setParseAction(lambda t: int(t[0]))
#TODO: use numString, and make integer if fiull stop

#TODO: allow parentheses? - should be ok as pass to the python parser

boolean_and = Literal("&").setResultsName("&")
boolean_or = Literal("|").setResultsName("|")
boolean = (boolean_and | boolean_or).setResultsName("boolean")

numericQuery = Group(attribute + comparison + float_string).setResultsName( "numericQuery")

stringValues = (Word(alphanums) | quotedString.setParseAction(removeQuotes)).setResultsName("value")

stringQuery =  Group(attribute + stringComparison + stringValues).setResultsName( "stringQuery")

singleQuery = numericQuery | stringQuery
nodeQuery = singleQuery + ZeroOrMore(boolean + singleQuery)

tests = [
        'Network = ACOnet & asn = 1853 & Latitude < 50',
        'Network = ACOnet & Longitude < 14',
        'asn = 680 & label = HAN',
        'Network = GEANT',
        'Network = GEANT & Country = Greece',
        'Network = GEANT & Latitude > 55',
        'Network = GEANT & type = "Fully Featured"',
        ]

def evaluate(stack):
    if len(stack) == 1:
        return set(stack.pop())
    else:
        a = set(stack.pop())
        op = stack.pop()
        return opn[op](a, evaluate(stack))

def query(qstring):
    if isinstance(qstring, str):
        result = nodeQuery.parseString(qstring)
    else:
# don't parse as likely came from edge parser
        result = qstring

#TODO: rearrange so remove stack and iterate over nodes only once
# so execute the boolean as function, rather than using stack on node sets
# ie test each node for all the required matches in one step
# and use data(=True) so get the dictionary reference once -> faster
# especially if using short circuits so when false stop executing

    def comp_fn_string(token, n):
        return opn[token.comparison](graph.node[n].get(token.attribute), token.value)

    def comp_fn_numeric(token, n):
        return opn[token.comparison](float(graph.node[n].get(token.attribute)), token.value)

    stack = []

    for token in result:
        if token in boolean:
            stack.append(token)
            continue

# different function depending on value type: numeric or string

        if isinstance(token.value, str):
            comp_fn = comp_fn_string
        if isinstance(token.value, float):
            comp_fn = comp_fn_numeric
       
        if comp_fn:
            #TODO: change to generator expressions and evaluate as sets in the evaluate function
            result_set = set(n for n in graph if token.attribute in graph.node[n] and comp_fn(token, n) )
            stack.append(result_set)

    final_set = evaluate(stack)
    return final_set

def nodes_to_labels(nodes):
    return  ", ".join(graph.node[n].get('label') for n in nodes)

def edges_to_labels(edges):
    return  ", ".join("%s->%s" % 
            (graph.node[u].get('label'), graph.node[v].get('label')) for (u,v) in edges)

# can set parse action to be return string?

#TODO: create function from the parsed result
# eg a lambda, and then apply this function to the nodes in the graph
# eg G.node[n].get(attribute) = "quotedstring"  operator 

for test in tests:
    print "--------------------------"
    print test
    test_result = query(test)
    print nodes_to_labels(test_result)
    #print result.dump()


edgeType = oneOf("<- <-> ->").setResultsName("edgeType")
edgeQuery = ("(" + nodeQuery.setResultsName("query_a") + ")"
        + edgeType
        + "(" + nodeQuery.setResultsName("query_b") + ")")


def find_edges(qstring):
    result = edgeQuery.parseString(qstring)
    set_a = query(result.query_a)
    set_b = query(result.query_b)
    select_type = result.edgeType

# use nbunch feature of networkx to limit edges to look at
    node_set = set_a | set_b

    edges = graph.edges(node_set)
# 1 ->, 2 <-, 3 <->

    def select_fn_u_to_v( (u, v), src_set, dst_set):
        """ u -> v"""
        return (u in src_set and v in dst_set)

    def select_fn_u_from_v( (u, v), src_set, dst_set):
        """ u <- v"""
        return (u in dst_set and v in src_set)

    def select_fn_v_to_from_u( (u, v), src_set, dst_set):
        """ u <- v"""
        return (u in src_set and v in dst_set) or (u in dst_set and v in src_set)

    if select_type == "->":
        select_function = select_fn_u_to_v
    elif select_type == "<-":
        select_function = select_fn_u_from_v
    elif select_type == "<->":
        select_function = select_fn_v_to_from_u 

    return ( e for e in edges if select_function(e, set_a, set_b))


#TODO: check if "<->" means join <- and -> or means bidirectional edge... or depends om Graph vs DiGraph?


#TODO: allow access to edge properties, eg (bob<->alice).freq returns 10
test_queries = [
        '(Network = GEANT) <-> (Network = GARR)',
        '(Network = GEANT) <-> (asn = 680)',
        ]

print "----edges:----"
for test in test_queries:
    matching_edges = find_edges(test)
    print edges_to_labels(matching_edges)
    print "---"


asn = "ASN"
asnAlias = (stringValues.setResultsName("network") + 
        "is" + asn + integer_string.setResultsName("asn")).setResultsName("asnAlias")
# eg AARNET is 213, sets asn of node AARNET
#'GEANT is ASN 123',

serviceString = (stringValues.setResultsName("provider")
        + "provides" + stringValues.setResultsName("service") 
        + "to" + stringValues.setResultsName("client")).setResultsName("serviceString")

relationshipString = (stringValues.setResultsName("provider")
        + "is a" + stringValues.setResultsName("relationship") 
        + "of" + stringValues.setResultsName("client")).setResultsName("relationshipString")


br_query = asnAlias | serviceString | relationshipString


test_queries = [
        'GEANT provides FBH to "Deutsche Telekom"',
        "ACOnet is a customer of GEANT",
        "ACOnet is a peer of 'Deutsche Telekom'",
        ]


test_queries = [
        "B is a customer of A",
"C is a customer of A",
"B is a peer of C",
"A provides freeBH to B",
"A provides freeBH to C",
]


G_business_relationship = nx.DiGraph()

print "----bus rel:----"
for test in test_queries:
    print test
    result = br_query.parseString(test)
    if "relationshipString" in result:
        G_business_relationship.add_edge(result.provider, result.client, attr=result.relationship)
    elif "serviceString" in result:
        G_business_relationship.add_edge(result.provider, result.client, attr=result.service)
    elif "asnAlias" in result:
        print "is service"

    print "---"

print G_business_relationship.edges(data=True)

"""
import matplotlib.pyplot as plt
pos=nx.spring_layout(G_business_relationship)

nx.draw(G_business_relationship, pos, font_size=18, arrows=False, node_color = "0.8", edge_color="0.8")

# NetworkX will automatically put a box behind label, make invisible
# by setting alpha to zero
bbox = dict(boxstyle='round',
        ec=(1.0, 1.0, 1.0, 0),
        fc=(1.0, 1.0, 1.0, 0.0),
        )      


edge_labels = dict( ((s,t), d.get('attr')) for s,t,d in G_business_relationship.edges(data=True))
nx.draw_networkx_edge_labels(G_business_relationship, pos, edge_labels, font_size=16, label_pos = 0.8, bbox = bbox)
plt.savefig("G_business_relationship.pdf")
"""


#------------------------------
# Stitching together
# alias = file
# gml or graphml
# abilene = "abilene.graphml"
# Connection: 
# push these into a dict indexed by alias
# or just use search matching? slower??
# need to know remapping of node ids...
# do remapping on load, based on size of previous loaded graphs? using generator...

alias = Word(alphanums).setResultsName("alias")
fileAlias = (alias + "=" + quotedString.setResultsName("file")).setResultsName("fileAlias")
graphNodeTuple = ("(" + stringValues.setResultsName("graph") + "," + stringValues.setResultsName("node") + ")")
interconnectString = (graphNodeTuple.setResultsName("gn_a") + "<->" 
        + graphNodeTuple.setResultsName("gn_b")).setResultsName("interconnectString")
graphDirString = ('graphdir =' + quotedString.setResultsName("dir")).setResultsName("graphDir")
stitchString = fileAlias | interconnectString | graphDirString

tests = [
        'dt = "Deutschetelekom.gml"',
        'hibernia = "Hiberniauk.gml"',
        'abvt = "Abvt.gml"',
        "(dt, Berlin) <-> (abvt, London)",
        '(dt, "New York") <-> (abvt, "New York")',
        "(dt, London) <-> (hibernia, London)",
        ]

graph_directory = "/Users/sk2/zoo/networks/master/sources/zoogml_geocoded"
graph_dict = {}
graph_interconnects = []
node_relabel_gen = itertools.count()

for test in tests:
    result = stitchString.parseString(test)
    if "graphDir" in result:
        graph_directory = result.graphdir
    elif "fileAlias" in result:
        filename = os.path.join(graph_directory, result.file)
#TODO: make support gml and graphml properly
        if "gml" in filename:
            graph_to_merge = nx.read_gml(filename)
        elif "graphml" in filename:
            graph_to_merge = nx.read_graphml(filename)
        # relabel
        graph_to_merge = graph_to_merge.to_undirected()
        mapping=dict(zip(graph_to_merge.nodes(), node_relabel_gen))
        graph_to_merge = nx.relabel_nodes(graph_to_merge, mapping)
        graph_dict[result.alias] = graph_to_merge
    elif "interconnectString" in result:
        graph_a = graph_dict[result.gn_a.graph]
        graph_b = graph_dict[result.gn_b.graph]
#pop to convert list of one item to single node
        node_a = [n for n in graph_a if graph_a.node[n].get("label") == result.gn_a.node].pop()
        node_b = [n for n in graph_b if graph_b.node[n].get("label") == result.gn_b.node].pop()
# And store for interconnects
        graph_interconnects.append( (node_a, node_b))

G_interconnect = nx.Graph()
for G in graph_dict.values():
    G_interconnect = nx.union(G_interconnect, G)

# and apply interconnectString
G_interconnect.add_edges_from(graph_interconnects)

#print G_interconnect.nodes(data=True)

"""
plt.clf()
pos=nx.spring_layout(G_interconnect)
labels = dict( (n, G_interconnect.node[n].get('label')) for n in G_interconnect)

nx.draw(G_interconnect, pos, labels=labels, arrows=False, font_size = 5, node_size = 20, node_color = "0.8", edge_color="0.8")
plt.savefig("G_interconnect.pdf")

G_interconnect.graph['name'] = "G_interconnect"


output_path = os.getcwd()
"""

"""
TopZooTools.geoplot.plot_graph(G_interconnect, output_path,
                    explode_scale=5,
                    use_labels=True,
                    edge_label_attribute= "speed",
                    label_font_size=4,
                    #use_bluemarble=True,
                    node_size = 20,
                    edge_font_size=8,
                    pdf=True,
                    country_color="#99CC99",
                    show_figure=True,
                    )
"""


originQuery = ("O(" +  
        nodeQuery.setResultsName("nodeQuery") + ")").setResultsName("originQuery")
transitQuery = ("T(" +  
        nodeQuery.setResultsName("nodeQuery") + ")").setResultsName("transitQuery")

bgpQuery = originQuery | transitQuery
tests = [
        'O(asn = 680)',
        'T(Network = GEANT)',
        ]


for test in tests:
    print test
    result = bgpQuery.parseString(test)
    matching_nodes = query(result.nodeQuery)
    print "matching nodes " + nodes_to_labels(matching_nodes)
    if "originQuery" in result:
        print "origin"

    elif "transitQuery" in result:
        print "transit"


bgpMatchAttribute = oneOf("prefix_list").setResultsName("bgpMatchAttribute")

prefixList = Literal("prefix_list")
matchComm = (prefixList.setResultsName("attribute")
        + comparison
        + attribute.setResultsName("value"))

bgpMatchQuery = (matchComm).setResultsName("bgpMatchQuery")

setComm = (Literal("setComm").setResultsName("attribute") 
        + integer_string.setResultsName("value")).setResultsName("setComm")
setLP = (Literal("setLP").setResultsName("attribute") 
        + integer_string.setResultsName("value")).setResultsName("setLP")
setMED = (Literal("setMED").setResultsName("attribute") 
        + integer_string.setResultsName("value")).setResultsName("setMED")

addTag = (Literal("addTag").setResultsName("attribute") 
        + attribute.setResultsName("value")).setResultsName("addTag")
removeTag = (Literal("removeTag").setResultsName("attribute") 
        + attribute.setResultsName("value")).setResultsName("removeTag")

setOriginAttribute = (Literal("setOriginAttribute").setResultsName("attribute") 
        + (oneOf("IGP BGP None").setResultsName("value"))).setResultsName("setOriginAttribute")

bgpAction = (setComm | setLP | setMED | addTag | removeTag | setOriginAttribute).setResultsName("bgpAction")

# Query may contain itself (nested)
bgpSessionQuery = Forward()
bgpSessionQuery << (
        Suppress("(") + 
        Group(Suppress("if") + bgpMatchQuery).setResultsName("if_clause") +
        Group(Suppress("then") + bgpAction).setResultsName("then_clause")
        + 
        Optional( Group(Suppress("else") + ( bgpAction | bgpSessionQuery )).setResultsName("else_clause"))
        + Suppress(")")
        ).setResultsName("bgpSessionQuery")

tests = [
        "(if prefix_list = pl_1 then setComm 100 else setComm 200)",
        "(if prefix_list =  pl_1 then setComm 100 else (if prefix_list = pl_2 then setLP 200))",
        "(if prefix_list =  pl_1 then setComm 100 else (if prefix_list = pl_2 then setOriginAttribute BGP else setComm 300))",
        ("(if prefix_list =  pl_1 then setComm 100 else (if prefix_list = pl_2 " 
        "then addTag free_bh else (if prefix_list = pl_3 then setLP 300 else setComm 400)))"),
]


def process_if_then_else(parsed_query):
    if "bgpSessionQuery" in parsed_query.else_clause:
# Nested query
                return { 
                'if': [parsed_query.if_clause.attribute, parsed_query.if_clause.comparison, 
                    parsed_query.if_clause.value],
                'then': [parsed_query.then_clause.attribute, parsed_query.then_clause.value],
                'else': process_if_then_else(parsed_query.else_clause.bgpSessionQuery),
                }

    elif parsed_query.else_clause:
                return {
                'if': [parsed_query.if_clause.attribute, parsed_query.if_clause.comparison, 
                    parsed_query.if_clause.value],
                'then': [parsed_query.then_clause.attribute, parsed_query.then_clause.value],
                'else': [parsed_query.else_clause.attribute, parsed_query.else_clause.value],
                }
    else:
        return {
                'if': [parsed_query.if_clause.attribute, parsed_query.if_clause.comparison, 
                    parsed_query.if_clause.value],
                'then': [parsed_query.then_clause.attribute, parsed_query.then_clause.value]
                }

parsedSessionResults = []

for test in tests:
    print test
    result =  bgpSessionQuery.parseString(test)
    #print result.dump()
    pprint.pprint( process_if_then_else(result))
    #res = ", ".join(['if', result.if_clause.attribute, result.if_clause.value,
    #    'then', result.then_clause.attribute, str(result.then_clause.value)])
    #pprint.pprint(res)
    parsedSessionResults.append(process_if_then_else(result))
    print

def printParsedSession(parseString, indent=""):
    print indent + "if (" + " ".join(elem for elem in parseString.get("if")) + "):"
    print indent + "  "  + " ".join(str(elem) for elem in parseString.get("then")) 
    if "else" in parseString:
        if isinstance(parseString.get("else"), dict):
            printParsedSession(parseString.get("else"), indent=indent + "  ")
        else:
            print indent + "else:"
            print indent + "  " + " ".join(str(elem) for elem in parseString.get("else")) 

for res in parsedSessionResults:
    printParsedSession (res)
    print

# need recursive function to process result

