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
#from pyparsing import *
from pyparsing import Literal, Word, alphas, alphanums, nums, Combine, Group, ZeroOrMore, Suppress, quotedString, removeQuotes, oneOf, Forward, Optional
import operator
import os
import pprint
import itertools
from collections import namedtuple
import sys
from pkg_resources import resource_filename
from mako.lookup import TemplateLookup



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
                '!=': operator.ne,
                '>=': operator.ge,
                '>': operator.gt,
                '&': set.intersection,
                '|': set.union,
                }

        self.match_tuple = namedtuple('match_tuple', "match_clauses, action_clauses, reject")
        self.match_clause = namedtuple('match_clause', 'type, comparison, value')
        self.action_clause = namedtuple('action_clause', 'action, value')

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
        self.u_egress = Literal("egress->").setResultsName("u_egress") 
        self.v_ingress = Literal("->ingress").setResultsName("v_ingress")
        self.u_ingress = Literal("ingress<-").setResultsName("u_ingress")
        self.v_egress = Literal("<-egress").setResultsName("v_egress") 
        edgeType = ( self.u_egress | self.u_ingress | self.v_egress | self.v_ingress).setResultsName("edgeType")
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
        rejectAction = (reject.setResultsName("attribute") +
                Literal("route").setResultsName("value")).setResultsName("reject")
        setNextHop = (Literal("setNextHop").setResultsName("attribute") + ipAddress.setResultsName("value")).setResultsName("setNextHop")

        setOriginAttribute = (Literal("setOriginAttribute").setResultsName("attribute") 
                + (oneOf("IGP BGP None").setResultsName("value"))).setResultsName("setOriginAttribute")

        bgpAction = Group(addTag | setLP | setMED | addTag | removeTag |
                setNextHop | setOriginAttribute | rejectAction).setResultsName("bgpAction")

        # The Clauses
        ifClause = Group(Suppress("if") + bgpMatchQuery 
                + ZeroOrMore(Suppress(boolean_and) + bgpMatchQuery)).setResultsName("if_clause")
        actionClause = bgpAction + ZeroOrMore(Suppress(boolean_and) + bgpAction)
        thenClause = Group(Suppress("then") + actionClause).setResultsName("then_clause")
        ifThenClause = Group(Suppress("(") + ifClause + 
                thenClause + Suppress(")")).setResultsName("ifThenClause")
        elseActionClause = Group(Suppress("(") + actionClause 
                + Suppress(")")).setResultsName("else_clause")

# Query may contain itself (nested)
        bgpSessionQuery = Forward()
        bgpSessionQuery << ( ifThenClause +
                Optional( Suppress("else") + (elseActionClause | bgpSessionQuery))
#+ ZeroOrMore(boolean_and + bgpAction) | bgpSessionQuery )).setResultsName("else_clause"))
                ).setResultsName("bgpSessionQuery")
        self.bgpSessionQuery = bgpSessionQuery

        self.bgpApplicationQuery = self.edgeQuery + Suppress(":") + self.bgpSessionQuery

    def apply_bgp_policy(self, network, qstring):
        result = self.bgpApplicationQuery.parseString(qstring)
        set_a = self.node_select_query(network, result.query_a)
        set_b = self.node_select_query(network, result.query_b)
        select_type = result.edgeType
        per_session_policy = qparser.process_if_then_else(result.bgpSessionQuery)

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

        if select_type in [self.u_egress, self.v_ingress]:
# u -> v
            select_function = select_fn_u_to_v
        if select_type in [self.u_ingress, self.v_egress]:
# u <- v
            select_function = select_fn_u_from_v

        # Determine which direction to apply policy to
        ingress_or_egress = None
        if select_type in [self.u_ingress, self.v_ingress]:
            ingress_or_egress = 'ingress'
        if select_type in [self.u_egress, self.v_egress]:
            ingress_or_egress = 'egress'

        # apply policy to edges
        selected_edges = ( e for e in edges if select_function(e, set_a, set_b))
        for u,v in selected_edges:
            network.g_session[u][v][ingress_or_egress].append(per_session_policy)

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
        retval = []
        for token in parsed_query:
            if token == parsed_query.else_clause:
# Special case of else (at end)
                reject = any(True for (action, value) in token if action == self.reject)
                else_tuples = [self.action_clause(action, value) for
                        (action, value) in token
                        if action != self.reject]
                retval.append(self.match_tuple([], else_tuples, reject))
            else:
                #TODO: check is in ifthen
                (if_clause, else_clause) = token
# Check for reject
                reject = any(True for (action, value) in else_clause if action == self.reject)
                if_tuples = [self.match_clause(attribute, comparison, value) for
                        (attribute, comparison, value) in if_clause]
                then_tuples = [self.action_clause(action, value) for
                        (action, value) in else_clause
                        if action != self.reject]
                retval.append(self.match_tuple(if_tuples, then_tuples, reject))
        return retval


#TODO: apply stringEnd to the matching parse queries to ensure have parsed all

graph = nx.read_gpickle("condensed_west_europe.pickle")

inet = ank.internet.Internet()
inet.load("condensed_west_europe.pickle")
ank.allocate_subnets(inet.network)
ank.initialise_bgp(inet.network)


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



policy_in_file = "policy.txt"
with open( policy_in_file, 'r') as f_pol:
    for line in f_pol.readlines():
        qparser.apply_bgp_policy(inet.network, line)

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


tests = [
        'dt = "Deutschetelekom.gml"',
        'hibernia = "Hiberniauk.gml"',
        'abvt = "Abvt.gml"',
        "(dt, Berlin) <-> (abvt, London)",
        '(dt, "New York") <-> (abvt, "New York")',
        "(dt, London) <-> (hibernia, London)",
        ]

# Don't use for now
tests = []

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

tests = [
        'O(asn = 680)',
        'T(Network = GEANT)',
        ]

# don't use for now
test = []
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

parsedSessionResults = []

template_cache_dir = config.template_cache_dir
template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )

quagga_bgp_policy_template = lookup.get_template("quagga/bgp_policy.mako")
junos_bgp_policy_template = lookup.get_template("junos/bgp_policy.mako")

route_map_tuple = namedtuple('route_map', "name, match_tuples")

def session_to_quagga(session_list):
    route_maps = []
    route_map_id = ("rm" + str(x) for x in itertools.count(1)) 
    for session in session_list: 
        sequence_number = itertools.count(10, 10)
        route_maps.append(route_map_tuple(route_map_id.next(), 
            [(sequence_number.next(), match_tuples) for match_tuples in session]))
#TODO: need to allocate community values (do this globally for network)
    return quagga_bgp_policy_template.render(
            route_maps = route_maps
            )

def session_to_junos(session_list):
    route_maps = []
    route_map_id = ("rm" + str(x) for x in itertools.count(1)) 
    for session in session_list: 
#TODO: need to reformat prefix list/matches
        term_number = itertools.count(1)
        route_maps.append(route_map_tuple(route_map_id.next(), 
            [(term_number.next(), match_tuples) for match_tuples in session]))
#TODO: need to allocate community values (do this globally for network)
    return junos_bgp_policy_template.render(
            route_maps = route_maps
            )

policy_out_file = "policy_output.txt"
with open( policy_out_file, 'w+') as f_pol:

    for node in inet.network.g_session:

        has_session_set = any( True for (src, dst, session_data) 
                in inet.network.g_session.in_edges(node, data=True) if len(session_data['ingress']) )
        if not has_session_set:
# check egress also
            has_session_set = any( True for (src, dst, session_data) 
                    in inet.network.g_session.out_edges(node, data=True) if len(session_data['egress']) )

        if has_session_set:
# only print name if session, otherwise huge list of nodes
            f_pol.write( "------------------------------\n")
            f_pol.write( "Policy on %s.%s\n" % (inet.network.label(node), inet.network.network(node)))
        # check sessions from this node
        for (src, dst, session_data) in inet.network.g_session.in_edges(node, data=True):
            if len(session_data['ingress']):
                f_pol.write( "session to: %s.%s\n" % (inet.network.label(src), inet.network.network(src)))
                f_pol.write( "ingress:\n")
                policy = session_data['ingress']
                f_pol.write(session_to_quagga(policy) + "\n")
                f_pol.write(session_to_junos(policy) + "\n")
        for (src, dst, session_data) in inet.network.g_session.out_edges(node, data=True):
            if len(session_data['egress']):
                f_pol.write( "session to: %s.%s\n" % (inet.network.label(dst), inet.network.network(dst)))
                f_pol.write( "egress:\n")
                policy = session_data['egress']
                f_pol.write(session_to_quagga(policy) + "\n")
                f_pol.write(session_to_junos(policy) +  "\n")
            
        
