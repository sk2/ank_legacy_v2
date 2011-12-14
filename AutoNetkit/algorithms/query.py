# -*- coding: utf-8 -*-
"""
Query
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

import networkx as nx
import logging
import AutoNetkit as ank
from AutoNetkit import config
LOG = logging.getLogger("ANK")
#TODO: only import from pyparsing what is needed
from pyparsing import *
import operator
import os
import pprint
import itertools
import TopZooTools
import TopZooTools.geoplot
import sys
from pkg_resources import resource_filename
from mako.lookup import TemplateLookup
from netaddr import IPNetwork



class queryParser:
    def __init__(self):
        attribute = Word(alphas, alphanums+'_').setResultsName("attribute")

        lt = Literal("<").setResultsName("<")
        le = Literal("<=").setResultsName("<=")
        eq = Literal("=").setResultsName("=")
        ne = Literal("!=").setResultsName("!=")
        ge = Literal(">=").setResultsName(">=")
        gt = Literal(">").setResultsName(">")

        self._opn = {
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
        ipField = Word(nums, max=3)
        ipAddress = Combine( ipField + "." + ipField + "." + ipField + "." + ipField ).setResultsName("ipAddress")

        boolean_and = Literal("&").setResultsName("&")
        boolean_or = Literal("|").setResultsName("|")
        boolean = (boolean_and | boolean_or).setResultsName("boolean")
        self._boolean = boolean # need to use in checking

        numericQuery = Group(attribute + comparison + float_string).setResultsName( "numericQuery")

        stringValues = (Word(alphanums) | quotedString.setParseAction(removeQuotes)).setResultsName("value")

        stringQuery =  Group(attribute + stringComparison + stringValues).setResultsName( "stringQuery")

        singleQuery = numericQuery | stringQuery
        self.nodeQuery = singleQuery + ZeroOrMore(boolean + singleQuery)

# edges
        edgeType = oneOf("<- <-> ->").setResultsName("edgeType")
        self.edgeQuery = ("(" + self.nodeQuery.setResultsName("query_a") + ")"
                + edgeType
                + "(" + self.nodeQuery.setResultsName("query_b") + ")")

# business relationship
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


        self.br_query = asnAlias | serviceString | relationshipString

# Stitching
        alias = Word(alphanums).setResultsName("alias")
        fileAlias = (alias + "=" + quotedString.setResultsName("file")).setResultsName("fileAlias")
        graphNodeTuple = ("(" + stringValues.setResultsName("graph") + "," + stringValues.setResultsName("node") + ")")
        interconnectString = (graphNodeTuple.setResultsName("gn_a") + "<->" 
                + graphNodeTuple.setResultsName("gn_b")).setResultsName("interconnectString")
        graphDirString = ('graphdir =' + quotedString.setResultsName("dir")).setResultsName("graphDir")
        self.stitchString = fileAlias | interconnectString | graphDirString


#start of BGP queries
        originQuery = ("O(" +  
                self.nodeQuery.setResultsName("nodeQuery") + ")").setResultsName("originQuery")
        transitQuery = ("T(" +  
                self.nodeQuery.setResultsName("nodeQuery") + ")").setResultsName("transitQuery")

        self.bgpQuery = originQuery | transitQuery

# bgp session query

        prefixList = Literal("prefix_list")
        matchPl = (prefixList.setResultsName("attribute")
                + comparison
                + attribute.setResultsName("value"))

        matchTag = (Literal("tag").setResultsName("attribute")
                + comparison
                + attribute.setResultsName("value"))

        bgpMatchQuery = Group(matchPl | matchTag).setResultsName("bgpMatchQuery")

        setLP = (Literal("setLP").setResultsName("attribute") 
                + integer_string.setResultsName("value")).setResultsName("setLP")
        setMED = (Literal("setMED").setResultsName("attribute") 
                + integer_string.setResultsName("value")).setResultsName("setMED")

        addTag = (Literal("addTag").setResultsName("attribute") 
                + attribute.setResultsName("value")).setResultsName("addTag")
        removeTag = (Literal("removeTag").setResultsName("attribute") 
                + attribute.setResultsName("value")).setResultsName("removeTag")
        #TODO: need to set blank value
        reject = Literal("reject")
#TODO: remove once move quagga output inside module
        self.reject = reject
        rejectAction = (reject.setResultsName("attribute") + Empty().setResultsName("value")).setResultsName("reject")
        setNextHop = (Literal("setNextHop").setResultsName("attribute") + ipAddress.setResultsName("value")).setResultsName("setNextHop")

        setOriginAttribute = (Literal("setOriginAttribute").setResultsName("attribute") 
                + (oneOf("IGP BGP None").setResultsName("value"))).setResultsName("setOriginAttribute")

        bgpAction = Group(addTag | setLP | setMED | addTag | removeTag |
                setNextHop | setOriginAttribute | rejectAction).setResultsName("bgpAction")

        # The Clauses
        ifClause = Group(Suppress("if") + bgpMatchQuery 
                + ZeroOrMore(boolean + bgpMatchQuery)).setResultsName("if_clause")
        actionClause = bgpAction + ZeroOrMore(boolean_and + bgpAction)
        thenClause = Group(Suppress("then") + actionClause).setResultsName("then_clause")
        ifThenClause = Suppress("(") + ifClause + thenClause + Suppress(")")
        elseActionClause = Group(Suppress("(") + actionClause 
                + Suppress(")")).setResultsName("else_clause")

# Query may contain itself (nested)
        bgpSessionQuery = Forward()
        bgpSessionQuery << ( ifThenClause +
                Optional( Suppress("else") + (elseActionClause + bgpSessionQuery))
#+ ZeroOrMore(boolean_and + bgpAction) | bgpSessionQuery )).setResultsName("else_clause"))
                ).setResultsName("bgpSessionQuery")
        self.bgpSessionQuery = bgpSessionQuery

    def find_bgp_sessions(self, network, qstring):
        result = self.edgeQuery.parseString(qstring)
        set_a = self.node_select_query(network, result.query_a)
        set_b = self.node_select_query(network, result.query_b)
        select_type = result.edgeType

# use nbunch feature of networkx to limit edges to look at
        node_set = set_a | set_b

        edges = network.g_session.edges(node_set)
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

    def evaluate_node_stack(self, stack):
        if len(stack) == 1:
            return set(stack.pop())
        else:
            a = set(stack.pop())
            op = stack.pop()
            return self._opn[op](a, self.evaluate_node_stack(stack))

    def node_select_query(self, network, qstring):
        if isinstance(qstring, str):
            result = self.nodeQuery.parseString(qstring)
        else:
# don't parse as likely came from edge parser
            result = qstring

#TODO: rearrange so remove stack and iterate over nodes only once
# so execute the boolean as function, rather than using stack on node sets
# ie test each node for all the required matches in one step
# and use data(=True) so get the dictionary reference once -> faster
# especially if using short circuits so when false stop executing

        def comp_fn_string(token, n):
            return self._opn[token.comparison](network.graph.node[n].get(token.attribute), token.value)

        def comp_fn_numeric(token, n):
            return self._opn[token.comparison](float(network.graph.node[n].get(token.attribute)), token.value)

        stack = []

        for token in result:
            if token in self._boolean:
                stack.append(token)
                continue

# different function depending on value type: numeric or string

            if isinstance(token.value, str):
                comp_fn = comp_fn_string
            if isinstance(token.value, float):
                comp_fn = comp_fn_numeric
        
            if comp_fn:
                #TODO: change to generator expressions and evaluate as sets in the evaluate function
                result_set = set(n for n in network.graph 
                        if token.attribute in network.graph.node[n] and comp_fn(token, n) )
                stack.append(result_set)

        final_set = self.evaluate_node_stack(stack)
        return final_set


    def process_if_then_else(self, parsed_query):
        print parsed_query.dump()
        return

        def parse_if(if_query):
            retval = []
            for token in if_query:
                if token in self._boolean:
                    retval.append(token)
                else:
                    retval.append([token.attribute, token.comparison, token.value])
            return retval

        def parse_then(then_query):
            retval = []
            for token in then_query:
                if token in self._boolean:
                    retval.append(token)
                else:
                    retval.append([token.attribute, token.value])
            return retval

        if "bgpSessionQuery" in parsed_query.else_clause:
# Nested query
                    return { 
                    'if': parse_if(parsed_query.if_clause),
                    'then': parse_then(parsed_query.then_clause),
# recursive call
                    'else': self.process_if_then_else(parsed_query.else_clause.bgpSessionQuery),
                    }

        elif parsed_query.else_clause:
                    return {
                    'if': parse_if(parsed_query.if_clause),
                    'then': parse_then(parsed_query.then_clause),
                    'else': parse_then(parsed_query.else_clause),
                    }
        else:
            return {
                    'if': parse_if(parsed_query.if_clause),
                    'then': parse_then(parsed_query.then_clause),
                    }


#TODO: apply stringEnd to the matching parse queries to ensure have parsed all

graph = nx.read_gpickle("condensed_west_europe.pickle")

inet = ank.internet.Internet()
inet.load("condensed_west_europe.pickle")
ank.allocate_subnets(inet.network, IPNetwork("10.0.0.0/8")) 
ank.initialise_bgp(inet.network)

#ank.jsplot(inet.network)
#TODO: initialise BGP sessions

#print inet.network.graph.nodes()

#print graph.nodes(data=True)

##### parser
# Node selection syntax

qparser = queryParser()

tests = [
        'Network = ACOnet & asn = 1853 & Latitude < 50',
        'Network = ACOnet & Longitude < 14',
        'asn = 680 & label = HAN',
        'Network = GEANT',
        'Network = GEANT & Country = Greece',
        'Network = GEANT & Latitude > 55',
        'Network = GEANT & type = "Fully Featured"',
        ]

def get_prefixes(inet, nodes):
    prefixes = set()
    for node in nodes:
        # Arbitrary choice of out edges, as bi-directional edge for each subnet
        prefixes.update([data.get("sn")
            for u, v, data in inet.network.graph.out_edges(node, data=True) 
            if data.get("sn")])
    #print prefixes
    

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
    #print "--------------------------"
    test_result = qparser.node_select_query(inet.network, test)
    #print nodes_to_labels(test_result)
    get_prefixes(inet, test_result)
    #print result.dump()


#TODO: check if "<->" means join <- and -> or means bidirectional edge... or depends om Graph vs DiGraph?

#TODO: allow access to edge properties, eg (bob<->alice).freq returns 10
#TODO: add ingress/egress to this
test_queries = [
        '(Network = GEANT) <-> (Network = GARR)',
        '(Network = GEANT) <-> (asn = 680)',
# and iBGP
        '(Network = GEANT) <-> (Network = GEANT)',
        ]

#TODO: wrap so have edge selection and policy combined

#print "----edges:----"
for test in test_queries:
    matching_edges = list(qparser.find_bgp_sessions(inet.network, test))
    #print edges_to_labels(matching_edges)
    #print "matches are %s" % matching_edges
    for (u,v) in matching_edges:
        #print inet.network.g_session[u][v]
        pass
    #print "---"

#sys.exit(0)

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

#print "----bus rel:----"
for test in test_queries:
    #print test
    result = qparser.br_query.parseString(test)
    if "relationshipString" in result:
        G_business_relationship.add_edge(result.provider, result.client, attr=result.relationship)
    elif "serviceString" in result:
        G_business_relationship.add_edge(result.provider, result.client, attr=result.service)
    elif "asnAlias" in result:
        print "is service"

    #print "---"

#print G_business_relationship.edges(data=True)

import matplotlib.pyplot as plt
"""
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
    result = qparser.stitchString.parseString(test)
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
#sys.exit(0)

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

tests = [
        'O(asn = 680)',
        'T(Network = GEANT)',
        ]

for test in tests:
    #print test
    result = qparser.bgpQuery.parseString(test)
    matching_nodes = qparser.node_select_query(inet.network, result.nodeQuery)
    #print "matching nodes " + nodes_to_labels(matching_nodes)
    if "originQuery" in result:
        #print "origin"
        pass

    elif "transitQuery" in result:
        #print "transit"
        pass

tests = [
        #"(if prefix_list = pl_1 then addTag a100)",
        "(if prefix_list = pl_1 then addTag a100) else (addTag a200)",
        "(if prefix_list = pl_1 then addTag a100 & setLP 90) else (removeTag a200)",
        "(if prefix_list = pl_1 then addTag a100 & setLP 90) else (addTag a200 & setLP 100)",
        "(if prefix_list = pl_1 & tag = aaa then addTag a100) else (addTag a200)",
        "(if prefix_list =  pl_1 then addTag a100) else (if prefix_list = pl_2 then setLP 200))",
        "(if prefix_list =  pl_1 then addTag a100 & reject) else (if prefix_list = pl_2 then setNextHop 1.2.3.4) else (addTag a300)",

]



parsedSessionResults = []

for test in tests:
    pass
    #print test
    #result =  qparser.bgpSessionQuery.parseString(test)
    #print result.dump()
    #res = ", ".join(['if', result.if_clause.attribute, result.if_clause.value,
    #    'then', result.then_clause.attribute, str(result.then_clause.value)])
    #parsedSessionResults.append(qparser.process_if_then_else(result))
    #print

def printParsedSession(parseString, indent=""):
    #TODO: make this work for multiple nesteds.....
    print indent + "if (" + " ".join(elem for elem in parseString.get("if")) + "):"
    print indent + "  "  + " ".join(str(elem) for elem in parseString.get("then")) 
    if "else" in parseString:
        if isinstance(parseString.get("else"), dict):
            printParsedSession(parseString.get("else"), indent=indent + "  ")
        else:
            print indent + "else:"
            print indent + "  " + " ".join(str(elem) for elem in parseString.get("else")) 

def parsedSessionVis(parsedSession):
    bbox = dict(boxstyle='round',
        ec=(1.0, 1.0, 1.0, 0),
        fc=(1.0, 1.0, 1.0, 0.0),
        )      

    parsed_graph = nx.DiGraph()
    next_node_id = itertools.count()
    def add_children(parent_node, parse_children, level):
        if_node_id = next_node_id.next()
        then_node_id = next_node_id.next()
        parsed_graph.add_node(if_node_id, label="if %s" % parse_children.get("if"),
                y = level*100, x = 0)
        parsed_graph.add_edge(parent_node, if_node_id, label="else")
        parsed_graph.add_node(then_node_id, label=parse_children.get("then"),
                y = level*100, x = 1)
        parsed_graph.add_edge(if_node_id, then_node_id, label="then")
        print "----"
        print parse_children
        if 'else' in parse_children:
            print "ELSE"
            if isinstance(parse_children.get("else"), dict):
# nested else
                add_children(if_node_id, parse_children.get("else"), level +1)
            else:
                print "add node"
                else_node_id = next_node_id.next()
                parsed_graph.add_node(else_node_id, label=parse_children.get("else"),
                        y = level*100 + 50, x=0)
                parsed_graph.add_edge(if_node_id, else_node_id, label="else")

        print "----"
        print
#TODO: add position info
    root_id = next_node_id.next()
    parsed_graph.add_node(root_id, label="start")
    add_children(root_id, parsedSession, level=1)

    #print parsed_graph.nodes(data=True)
    #print parsed_graph.edges(data=True)

# remove placeholder node
    parsed_graph.remove_node(root_id)

    plt.clf()
    pos=nx.spring_layout(parsed_graph)
    print pos
    pos = dict( (n, (d['x'], -1*d['y'])) for n,d in parsed_graph.nodes(data=True))
    labels = dict( (n, parsed_graph.node[n].get('label')) for n in parsed_graph)
    nx.draw(parsed_graph, pos, labels=labels, arrows=False,
            font_size = 12, node_size = 50, node_color = "0.8", edge_color="0.8")
    edge_labels = dict( ((s,t), d.get('label')) 
            for s,t,d in parsed_graph.edges(data=True))
    nx.draw_networkx_edge_labels(parsed_graph, pos, 
        edge_labels, font_size=16, label_pos = 0.5, bbox = bbox)
    plt.savefig("parsed_graph.pdf")


template_cache_dir = config.template_cache_dir
template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )

quagga_bgp_policy_template = lookup.get_template("quagga/bgp_policy.mako")
junos_bgp_policy_template = lookup.get_template("junos/bgp_policy.mako")

def session_to_quagga(session):
    route_maps = {}
    sequence_number = itertools.count(10, 10)

#TODO: need to reformat prefix list/matches

    def flatten_nested_dicts(pol_dict):
        retval = []
# remove & as match on all conditions
        if_clause = [item for item in pol_dict.get("if") if item != "&"]
        then_clause = [item for item in pol_dict.get("then") if item != "&"]
        reject = any(True for (attribute, value) in then_clause if attribute == qparser.reject)
        retval.append((sequence_number.next(), if_clause, then_clause, reject))
        if 'else' in pol_dict:
            if isinstance(pol_dict.get("else"), dict):
                retval += flatten_nested_dicts(pol_dict.get("else"))
            else:
# No match clause, so match clause is empty list 
                else_clause = [item for item in pol_dict.get("else") if item != "&"]
                reject = any(True for (attribute, value) in else_clause if attribute == qparser.reject)
                retval.append((sequence_number.next(), [], else_clause, reject))

        return retval

    route_maps["rm1"] =  flatten_nested_dicts(session)
#TODO: need to allocate community values (do this globally for network)
    print quagga_bgp_policy_template.render(
            route_maps = route_maps
            )

def session_to_junos(session):
    route_maps = {}
#TODO: need to reformat prefix list/matches
    term_number = itertools.count(1)

    def flatten_nested_dicts(pol_dict):
        retval = []
# remove & as match on all conditions
        if_clause = [item for item in pol_dict.get("if") if item != "&"]
        then_clause = [item for item in pol_dict.get("then") if item != "&"]
#TODO: move the reject handling into the parser itself
        reject = any(True for (attribute, value) in then_clause if attribute == qparser.reject)
#TODO: use named tuples
        retval.append((term_number.next(), if_clause, then_clause, reject))
        if 'else' in pol_dict:
            if isinstance(pol_dict.get("else"), dict):
                retval += flatten_nested_dicts(pol_dict.get("else"))
            else:
# No match clause, so match clause is empty list 
                else_clause = [item for item in pol_dict.get("else") if item != "&"]
                reject = any(True for (attribute, value) in else_clause if attribute == qparser.reject)
                retval.append((term_number.next(), [], else_clause, reject))

        return retval

    route_maps["rm1"] =  flatten_nested_dicts(session)
#TODO: need to allocate community values (do this globally for network)
    print junos_bgp_policy_template.render(
            route_maps = route_maps
            )


def parser2(result):
    retval = []
    print "-----"

    #TODO: remove when move into qparser
    boolean = qparser._boolean
    retval = []

    print


for test in tests:
    print test
    result =  qparser.bgpSessionQuery.parseString(test)
    #print result.dump()
    #res = ", ".join(['if', result.if_clause.attribute, result.if_clause.value,
    #    'then', result.then_clause.attribute, str(result.then_clause.value)])
    processed = qparser.process_if_then_else(result)
    #session_to_quagga(processed)
    #session_to_junos(processed)


# need recursive function to process result

