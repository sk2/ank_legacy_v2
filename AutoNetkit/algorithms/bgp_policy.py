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
from pyparsing import Literal, Word, alphas, alphanums, nums, Combine, Group, ZeroOrMore, Suppress, quotedString, removeQuotes, oneOf, Forward, Optional
import pyparsing
import operator
import pprint
import itertools
from collections import namedtuple


# logging hacks
import logging
import logging.handlers

LEVELS = {'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL}


#TODO: load logger settings from config file
logger = logging.getLogger("ANK")
logger.setLevel(logging.DEBUG)

#TODO: check settings are being loaded from file correctly
# and that handlers are being correctly set - as default level appearing

ch = logging.StreamHandler()
# Use debug from settings

formatter = logging.Formatter('%(levelname)-6s %(message)s')

ch.setLevel(logging.DEBUG)
#ch.setLevel(logging.INFO)

ch.setFormatter(formatter)

logging.getLogger('').addHandler(ch)



class BgpPolicyParser:
    def __init__(self, network):
        self.network = network


        # Grammars
        attribute = Word(alphas, alphanums+'_').setResultsName("attribute")

        lt = Literal("<").setResultsName("<")
        le = Literal("<=").setResultsName("<=")
        eq = Literal("=").setResultsName("=")
        ne = Literal("!=").setResultsName("!=")
        ge = Literal(">=").setResultsName(">=")
        gt = Literal(">").setResultsName(">")
        wildcard = Literal("*").setResultsName("wildcard")
        self.wildcard = wildcard

        self.prefix_lists = {}
        self.tags_to_allocate = set()
        self.allocated_tags = {}

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

        # map alphanum chars to alphanum equivalents for use in tags
        self._opn_to_tag = {
                '<': "lt",
                '<=': "le",
                '=': "eq",
                '!=': "ne",
                '>=': "ge",
                '>': "gt",
                '&': "and",
                '|': "or",
                }

        self.match_tuple = namedtuple('match_tuple', "match_clauses, action_clauses, reject")
        self.match_tuple_with_seq_no = namedtuple('match_tuple', "seq_no, match_clauses, action_clauses, reject")
        self.route_map_tuple = namedtuple('route_map', "name, match_tuples")
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

        stringValues = (Word(alphanums) | quotedString.setParseAction(removeQuotes)
                ).setResultsName("value")

        stringQuery =  Group(attribute + stringComparison + stringValues).setResultsName( "stringQuery")
        wildcardQuery = wildcard.setResultsName("wildcardQuery")

        singleQuery = numericQuery | stringQuery | wildcardQuery
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

#start of BGP queries
        originQuery = (Literal("Origin").setResultsName("attribute") + 
                #this is a workaround for the match, comparison, value 3-tuple in processing
                Literal("(").setResultsName("comparison") +  
                Group(self.nodeQuery).setResultsName("value") + Suppress(")")).setResultsName("originQuery")
        transitQuery = (Literal("Transit").setResultsName("attribute") +
                #this is a workaround for the match, comparison, value 3-tuple in processing
                Literal("(").setResultsName("comparison") +  
                Group(self.nodeQuery).setResultsName("value") + Suppress(")")).setResultsName("transitQuery")

        prefixList = Literal("prefix_list")
        matchPl = (prefixList.setResultsName("attribute")
                + comparison
                + attribute.setResultsName("value"))

        matchTag = (Literal("tag").setResultsName("attribute")
                + comparison
                + attribute.setResultsName("value"))

        bgpMatchQuery = Group(matchPl | matchTag | originQuery | transitQuery ).setResultsName("bgpMatchQuery")

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

    def apply_bgp_policy(self, qstring):
        result = self.bgpApplicationQuery.parseString(qstring)
        set_a = self.node_select_query(self.network, result.query_a)
        set_b = self.node_select_query(self.network, result.query_b)
        select_type = result.edgeType
        per_session_policy = self.process_if_then_else(self.network, result.bgpSessionQuery)

# use nbunch feature of networkx to limit edges to look at
        node_set = set_a | set_b

        edges = self.network.g_session.edges(node_set)
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
            self.network.g_session[u][v][ingress_or_egress].append(per_session_policy)

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
# especially if using short circuits so when False stop executing

        def comp_fn_string(token, n):
            #TODO: allow partial string matches - beginswith, endswith, etc - map to python functions
            return self._opn[token.comparison](network.graph.node[n].get(token.attribute), token.value)

        def comp_fn_numeric(token, n):
            return self._opn[token.comparison](float(network.graph.node[n].get(token.attribute)), token.value)

        stack = []

        for token in result:
            if token in self._boolean:
                stack.append(token)
                continue

# different function depending on value type: numeric or string

            
            if token == self.wildcard:
                result_set = set(n for n in network.graph )
                stack.append(result_set)
                continue
            elif token.attribute == "node":
                result_set = set([token.value])
                stack.append(result_set)
                continue
            elif isinstance(token.value, str):
                comp_fn = comp_fn_string
            elif isinstance(token.value, float):
                comp_fn = comp_fn_numeric
        
            if comp_fn:
                #TODO: change to generator expressions and evaluate as sets in the evaluate function
                result_set = set(n for n in network.graph 
                        if token.attribute in network.graph.node[n] and comp_fn(token, n) )
                stack.append(result_set)

        final_set = self.evaluate_node_stack(stack)
        return final_set

    def allocate_tags(self):
        tag_id = itertools.count(10,10)
        for tag in self.tags_to_allocate:
            self.allocated_tags[tag] = "1234:%s" % tag_id.next()


    def get_prefixes(inet, network, nodes):
        prefixes = set()
        for node in nodes:
            # Arbitrary choice of out edges, as bi-directional edge for each subnet
            prefixes.update([data.get("sn")
                for u, v, data in network.graph.out_edges(node, data=True) 
                if data.get("sn")])

        return prefixes

    def query_to_tag(self, query):
        """ flattens a node select query into a tag
        TODO: convert this to proper testable docstring
        eg (asn=3) becomes asn_eq_3
        """
# flatten items into single list in lexicographic order
        retval = (item for sublist in query for item in sublist)
# replace char if in mapping, else leave, eg = -> eq
        retval = (self._opn_to_tag[item] if item in self._opn_to_tag else item
                for item in retval)
# ensure all strings
# format integers as strings with no decimal points
        retval = ("%i"%item if isinstance(item, float) and int(item) == item else item
                for item in retval)
        retval = (str(item).lower() for item in retval)
        return "_".join(retval)

    def tag_to_pl(self, tag):
        return "pl_%s" % tag

    def tag_to_cl(self, tag):
        return "cl_%s" % tag

    def proc_ot_match(self, network, match_type, match_query):
# extract the node queryParser
#TODO: handle case of multiple matches......
# rather than getting first element, iterate over
        nodes = self.node_select_query(network, match_query)
        tag = self.query_to_tag(match_query)
        tag_pl = self.tag_to_pl(tag)
        tag_cl = self.tag_to_cl(tag)
# efficiency: check if query has already been executed (ie if already prefixes for this tag)
#TODO: see if need to have unique name for prefix list and comm val: eg pl_tag and 
        if tag_pl in self.prefix_lists:
            print "already executed prefix lookup for", tag_pl
        else:
            prefixes = self.get_prefixes(network, nodes)
            self.prefix_lists[tag_pl] = prefixes
# and mark prefixes
            for node in nodes:
                apply_prefix_query = ("(node = %s) egress-> (*): "
                        "(if prefix_list = %s then addTag %s)") % (node, tag_pl, tag_cl)
                print apply_prefix_query
                self.apply_bgp_policy(network, apply_prefix_query)

# store tag
            self.tags_to_allocate.update([tag])
        return self.match_clause("tag", "=", tag)


        #matching_nodes = self.node_select_query(network, ot_match.value)
        #print "matching nodes", matching_nodes


#TODO: make network a variable in the qparser class???

    def process_if_then_else(self, network, parsed_query):
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
                (if_clause, then_clause) = token
#TODO: base this on the keywords used in the parser itself for continuity
                origin_transit_keywords = set(["Origin", "Transit"])
# Check for reject
                if_tuples = [
                        self.proc_ot_match(network, attribute, value) if attribute in origin_transit_keywords
                        else self.match_clause(attribute, comparison, value)
                        for (attribute, comparison, value) in if_clause]
                reject = any(True for (action, value) in then_clause if action == self.reject)
                then_tuples = [self.action_clause(action, value) for
                        (action, value) in then_clause
                        if action != self.reject]
                retval.append(self.match_tuple(if_tuples, then_tuples, reject))
        return retval

    def cl_and_pl_per_node(self):
        # extract tags and prefixes used from sessions
        for node in self.network.g_session:
            prefixes = set()
            tags = set()
# also sets routemap names
            for (dst, src, session_data) in self.network.g_session.in_edges(node, data=True):
                counter = itertools.count(1)
                session_policy_tuples = []
                for match_tuples in session_data['ingress']:
                    seq_no = itertools.count(1)
                    match_tuples_with_seqno = []
                    for match_tuple in match_tuples:
                        for match_clause in match_tuple.match_clauses:
                            if 'prefix_list' in match_clause.type:
                                prefixes.update([match_clause.value])
                            if 'tag' in match_clause.type:
                                tags.update([match_clause.value])
                        for action_clause in match_tuple.action_clauses:
                            if action_clause.action in set(['addTag']):
                                tags.update([action_clause.value])
                        match_tuples_with_seqno.append(self.match_tuple_with_seq_no(seq_no.next(), 
                            match_tuple.match_clauses, match_tuple.action_clauses, match_tuple.reject))
                    route_map_name = "rm_ingress_%s_%s" % (self.network.label(dst).replace(".", "_"), counter.next())
# allocate sequence number
                    session_policy_tuples.append(self.route_map_tuple(route_map_name, match_tuples_with_seqno))
                # Update with the named policy tuples
                self.network.g_session[dst][src]['ingress'] = session_policy_tuples

            for (src, dst, session_data) in self.network.g_session.out_edges(node, data=True):
                counter = itertools.count(1)
                session_policy_tuples = []
                for match_tuples in session_data['egress']:
                    seq_no = itertools.count(1)
                    match_tuples_with_seqno = []
                    for match_tuple in match_tuples:
                        for match_clause in match_tuple.match_clauses:
                            if 'prefix_list' in match_clause.type:
                                prefixes.update([match_clause.value])
                            if 'tag' in match_clause.type:
                                tags.update([match_clause.value])
                        for action_clause in match_tuple.action_clauses:
                            if action_clause.action in set(['addTag']):
                                tags.update([action_clause.value])
                        match_tuples_with_seqno.append(self.match_tuple_with_seq_no(seq_no.next(), 
                            match_tuple.match_clauses, match_tuple.action_clauses, match_tuple.reject))
                    route_map_name = "rm_egress_%s_%s" % (self.network.label(dst).replace(".", "_"), 
                            counter.next())
# allocate sequence number
                    session_policy_tuples.append(self.route_map_tuple(route_map_name, match_tuples_with_seqno))
                # Update with the named policy tuples
                self.network.g_session[src][dst]['egress'] = session_policy_tuples

            self.network.g_session.node[node]['tags'] = tags
            self.network.g_session.node[node]['prefixes'] = prefixes
# and update the global list of tags with any new tags found
            self.tags_to_allocate.update(tags)

    def store_tags_per_router(self):
        for node, data in self.network.g_session.nodes(data=True):
            tags = dict.fromkeys(data['tags'])
            for tag in tags:
                tags[tag] = self.allocated_tags[tag]
            # store updated tags
            self.network.g_session.node[node]['tags'] = tags

            prefixes = dict.fromkeys(data['prefixes'])
            for prefix in prefixes:
                prefixes[prefix] = self.prefix_lists[prefix]
            # store updated tags
            self.network.g_session.node[node]['prefixes'] = prefixes


    def apply_policy_file(self, policy_in_file):
        with open( policy_in_file, 'r') as f_pol:
            for line in f_pol.readlines():
                if line.strip() == "":
# blank line
                    continue
                self.apply_bgp_policy(self.network, line)
        self.cl_and_pl_per_node()
        self.allocate_tags()
        self.store_tags_per_router()

