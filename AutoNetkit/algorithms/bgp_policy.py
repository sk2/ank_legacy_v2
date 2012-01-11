# -*- coding: utf-8 -*-
"""
Parse BGP policy from a file. 

.. warning::

    Work in progress.

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

LOG = logging.getLogger("ANK")


def tag_to_pl(tag):
    """Adds prefix list prefix to tag

    >>> tag_to_pl("network_eq_as1")
    'pl_network_eq_as1'
    """
    return "pl_%s" % tag

def tag_to_cl(tag):
    """Adds community list prefix to tag

    >>> tag_to_cl("network_eq_as1")
    'cl_network_eq_as1'
    
    """
    return "cl_%s" % tag


#TODO: see if can return in a data structure that pretty-print works nicely on
class match_tuple (namedtuple('match_tuple', "match_clauses, action_clauses, reject")):
    __slots__ = ()
    def __repr__(self):
        return "%s, %s, reject=%s" % (self.match_clauses, self.action_clauses, self.reject)

class match_tuple_with_seq_no (namedtuple('match_tuple', "seq_no, match_clauses, action_clauses, reject")):
    __slots__ = ()
    def __repr__(self):
        return "seq%s %s %s reject=%s" % (self.seq_no, 
                self.match_clauses, 
                self.action_clauses, 
                self.reject)

class route_map_tuple (namedtuple('route_map', "name, match_tuples")):
    __slots__ = ()
    def __repr__(self):
        return "%s %s" % (self.name, self.match_tuples)

class match_clause (namedtuple('match_clause', 'type, comparison, value')):
    __slots__ = ()
    def __repr__(self):
        return "%s %s %s" % (self.type, self.comparison, self.value)

class action_clause (namedtuple('action_clause', 'action, value')):
    __slots__ = ()
    def __repr__(self):
        return "%s %s" % (self.action, self.value)


class BgpPolicyParser:
    """Parser class"""
    def __init__(self, network):
        self.network = network
        self.g_business_relationship = nx.DiGraph()

        # Grammars
        attribute = Word(alphanums+'_'+".").setResultsName("attribute")
        self.attribute = attribute

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

#TODO fix this matching 2a.ab when that should match a string
        numericQuery = Group(attribute + comparison + float_string).setResultsName( "numericQuery")

        stringValues = (attribute | quotedString.setParseAction(removeQuotes)
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

        bgpAction = Group(addTag | setLP | setMED | removeTag |
                setNextHop | setOriginAttribute | rejectAction).setResultsName("bgpAction")

        # The Clauses
        ifClause = Group(Suppress("if") + bgpMatchQuery 
                + ZeroOrMore(Suppress(boolean_and) + bgpMatchQuery)).setResultsName("if_clause")
        actionClause = bgpAction + ZeroOrMore(Suppress(boolean_and) + bgpAction)
        thenClause = Group(Suppress("then") + actionClause).setResultsName("then_clause")
        ifThenClause = Group(Suppress("(") + 
                ifClause + thenClause + Suppress(")")).setResultsName("ifThenClause")
        elseActionClause = Group(Suppress("(") + actionClause 
                + Suppress(")")).setResultsName("else_clause")
# Support actions without a condition (ie no "if")
        unconditionalAction =  Group(Suppress("(")
            + Group(actionClause).setResultsName("unconditionalActionClause")
            + Suppress(")")).setResultsName("bgpSessionQuery")

# Query may contain itself (nested)
        bgpSessionQuery = Forward()
        bgpSessionQuery << ( ifThenClause +
                Optional( Suppress("else") + (elseActionClause | bgpSessionQuery))
#+ ZeroOrMore(boolean_and + bgpAction) | bgpSessionQuery )).setResultsName("else_clause"))
                ).setResultsName("bgpSessionQuery")
        bgpSessionQuery =  bgpSessionQuery | unconditionalAction
        self.bgpSessionQuery = bgpSessionQuery


#todo: remove testing
        self.stringQuery = stringQuery

        self.bgpApplicationQuery = self.edgeQuery + Suppress(":") + self.bgpSessionQuery

# business relationship building
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

    def apply_bgp_policy(self, qstring):
        """Applies policy to network 


        >>> pol_parser = ank.BgpPolicyParser(ank.network.Network(ank.load_example("multias")))

#TODO: move these tests out

        Testing internals:

        >>> attributestring = "2a.as1"
        >>> result = pol_parser.attribute.parseString(attributestring)

        Node and edge queries:

        >>> nodestring = "node = '2ab.ab'"
        >>> result = pol_parser.nodeQuery.parseString(nodestring)
        >>> result = pol_parser.edgeQuery.parseString("(" + nodestring + ") egress-> (node = b)")
        >>> result = pol_parser.edgeQuery.parseString("(node = a.b) egress-> (node = b)")

        Full policy queries:

        >>> pol_parser.apply_bgp_policy("(node = '2a.AS2') egress-> (*): (if prefix_list = pl_asn_eq_2 then addTag cl_asn_eq_2)")
        >>> pol_parser.apply_bgp_policy("(Network = AS1 ) ->ingress (Network = AS2): (if tag = deprefme then setLP 90) ")
        >>> pol_parser.apply_bgp_policy("(Network = AS1 ) ->ingress (Network = AS2): (addTag ABC & setLP 90) ")
        >>> pol_parser.apply_bgp_policy("(asn = 1) egress-> (asn = 1): (if Origin(asn=2) then addTag a100 )")
        >>> pol_parser.apply_bgp_policy("(asn = 1) egress-> (asn = 1): (if Transit(asn=2) then addTag a100 )")
        >>> pol_parser.apply_bgp_policy("(node = a_b ) ->ingress (Network = AS2): (addTag ABC & setLP 90) ")
        """
        LOG.debug("Applying policy %s" % qstring)
        result = self.bgpApplicationQuery.parseString(qstring)
        LOG.debug("Query string is %s " % qstring)
        set_a = self.node_select_query(result.query_a)
        LOG.debug("Set a is %s " % set_a)
        set_b = self.node_select_query(result.query_b)
        LOG.debug("Set b is %s " % set_b)
        select_type = result.edgeType
        per_session_policy = self.process_if_then_else(result.bgpSessionQuery)

# use nbunch feature of networkx to limit edges to look at
        node_set = set_a | set_b

        edges = self.network.g_session.edges(node_set)
        LOG.debug("Edges are %s " % edges)
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
        selected_edges = list( e for e in edges if select_function(e, set_a, set_b))
        LOG.info("Selected edges are %s" % selected_edges)
        for u,v in selected_edges:
            LOG.debug("Applying policy %s to %s of %s->%s" % ( per_session_policy, ingress_or_egress, 
                self.network.fqdn(u), self.network.fqdn(v)))
            self.network.g_session[u][v][ingress_or_egress].append(per_session_policy)
    def evaluate_node_stack(self, stack):
        """Evaluates a stack of nodes with join queries"""
        LOG.debug("Evaluating node stack %s" % stack)
        if len(stack) == 1:
            return set(stack.pop())
        else:
            a = set(stack.pop())
            op = stack.pop()
            return self._opn[op](a, self.evaluate_node_stack(stack))

    def node_select_query(self, qstring):
        """
        >>> pol_parser = ank.BgpPolicyParser(ank.network.Network(ank.load_example("multias")))
        >>> pol_parser.node_select_query("asn = 1")
        set(['n0', 'n1', 'n3'])
        >>> pol_parser.node_select_query("name = a.b")
        set([])
        >>> pol_parser.node_select_query("name = a_b")
        set([])
        """
        LOG.debug("Processing node select query %s" % qstring)
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
            return self._opn[token.comparison](self.network.graph.node[n].get(token.attribute), token.value)

        def comp_fn_numeric(token, n):
            return self._opn[token.comparison](float(self.network.graph.node[n].get(token.attribute)), token.value)

        stack = []

        for token in result:
            if token in self._boolean:
                stack.append(token)
                continue

# different function depending on value type: numeric or string
            if token == self.wildcard:
                result_set = set(n for n in self.network.routers() )
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
                result_set = set(n for n in self.network.graph 
                        if token.attribute in self.network.graph.node[n] and comp_fn(token, n) )
                stack.append(result_set)

        final_set = self.evaluate_node_stack(stack)
        return final_set

    def allocate_tags(self):
        """Allocates community values to tags"""
        LOG.debug("Allocating community values to tags")
        tag_id = itertools.count(1)
        generic_asn = "1234"
        for tag in self.tags_to_allocate:
            self.allocated_tags[tag] = "%s:%s" % (generic_asn, tag_id.next() * 10)


    def get_prefixes(self, nodes):
        """Returns prefixes for given node set"""
        LOG.debug("Returning prefixes for nodes %s" % nodes)
        prefixes = set()
        for node in nodes:
            # Arbitrary choice of out edges, as bi-directional edge for each subnet
            prefixes.update([data.get("sn")
                for u, v, data in self.network.graph.out_edges(node, data=True) 
                if data.get("sn")])

        return prefixes

    def query_to_tag(self, query):
        """ flattens a node select query into a tag
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

    def proc_ot_match(self, match_type, match_query):
        """Processes origin or transit match query"""
        LOG.debug("Processing Origin/Transit query %s %s" % (match_type, match_query))
# extract the node queryParser
#TODO: handle case of multiple matches......
# rather than getting first element, iterate over
#TODO: need to handle origin different here to transit - diff policy
        nodes = self.node_select_query(match_query)
        tag = self.query_to_tag(match_query)
        tag_pl = tag_to_pl(tag)
        tag_cl = tag_to_cl(tag)
        if match_type == "Transit":
                policy = "(addTag %s)" % tag_cl
                LOG.info("Transit policy: %s" % policy)
        else:

# efficiency: check if query has already been executed (ie if already prefixes for this tag)
#TODO: see if need to have unique name for prefix list and comm val: eg pl_tag and 
            if tag_pl in self.prefix_lists:
                LOG.debug( "already executed prefix lookup for", tag_pl)
            else:
                prefixes = self.get_prefixes(nodes)
                self.prefix_lists[tag_pl] = prefixes
# and mark prefixes
                policy = "(if prefix_list = %s then addTag %s)" % (tag_pl, tag_cl)
                LOG.info("Origin policy: %s" % policy)
# now apply policy to all egress from nodes
# store tag
                self.tags_to_allocate.update([tag])


        # Parse the string into policy tuples
        parsed = self.bgpSessionQuery.parseString(policy)
        per_session_policy = self.process_if_then_else(parsed.bgpSessionQuery)

        for node in nodes:
            for u, v in self.network.g_session.out_edges(node):
                LOG.info("Applying O/T policy to %s egress -> %s" % (u, v))
                self.network.g_session[u][v]['egress'].append(per_session_policy)
        return match_clause("tag", "=", tag_cl)

    def process_if_then_else(self, parsed_query):
        """Processes if-then-else query"""
        LOG.debug("Processing if-then-else query %s" % parsed_query)
        retval = []

        for token in parsed_query:
            if not parsed_query.ifThenClause:
# Special case of action only clause (no "if" clause)
                reject = any(True for (action, value) in token if action == self.reject)
                else_tuples = [action_clause (action, value) for
                        (action, value) in token
                        if action != self.reject]
                retval.append(match_tuple([], else_tuples, reject))

            elif token == parsed_query.else_clause:
# Special case of else (at end)
                reject = any(True for (action, value) in token if action == self.reject)
                else_tuples = [action_clause (action, value) for
                        (action, value) in token
                        if action != self.reject]
                retval.append(match_tuple([], else_tuples, reject))
            else:
                #TODO: check is in ifthen
                (if_clause, then_clause) = token
#TODO: base this on the keywords used in the parser itself for continuity
                origin_transit_keywords = set(["Origin", "Transit"])
# Check for reject
                if_tuples = [
                        self.proc_ot_match(attribute, value) if attribute in origin_transit_keywords
                        else match_clause(attribute, comparison, value)
                        for (attribute, comparison, value) in if_clause]
                reject = any(True for (action, value) in then_clause if action == self.reject)
                then_tuples = [action_clause (action, value) for
                        (action, value) in then_clause
                        if action != self.reject]
                retval.append(match_tuple(if_tuples, then_tuples, reject))
        return retval

    def cl_and_pl_per_node(self):
        """extract tags and prefixes used from sessions
        Also applies sequence numbers to match clauses"""
        LOG.debug("Extracting community lists and prefix lists per node, adding sequence numbers")
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
                        match_tuples_with_seqno.append(match_tuple_with_seq_no(seq_no.next(), 
                            match_tuple.match_clauses, match_tuple.action_clauses, match_tuple.reject))
                    route_map_name = "rm_ingress_%s_%s" % (self.network.fqdn(dst).replace(".", "_"), counter.next())
# allocate sequence number
                    session_policy_tuples.append(route_map_tuple(route_map_name, match_tuples_with_seqno))
                # Update with the named policy tuples
                LOG.debug("Storing session tuples %s to %s %s ingress" % (session_policy_tuples, self.network.fqdn(src), self.network.fqdn(dst)))
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
                        match_tuples_with_seqno.append(match_tuple_with_seq_no(seq_no.next(), 
                            match_tuple.match_clauses, match_tuple.action_clauses, match_tuple.reject))
                    route_map_name = "rm_egress_%s_%s" % (self.network.fqdn(dst).replace(".", "_"), 
                            counter.next())
# allocate sequence number
                    session_policy_tuples.append(route_map_tuple(route_map_name, match_tuples_with_seqno))
                # Update with the named policy tuples
                self.network.g_session[src][dst]['egress'] = session_policy_tuples
                LOG.debug("Storing session tuples %s to %s %s egress" % (session_policy_tuples, self.network.fqdn(src), self.network.fqdn(dst)))

            self.network.g_session.node[node]['tags'] = tags
            self.network.g_session.node[node]['prefixes'] = prefixes
# and update the global list of tags with any new tags found
            self.tags_to_allocate.update(tags)

    def store_tags_per_router(self):
        """Stores the list of tags/community value mappings in the router in session graph"""
        LOG.debug("Storing allocated tags to routers")
        for node, data in self.network.g_session.nodes(data=True):
            tags = dict( (tag, self.allocated_tags[tag]) for tag in data['tags'])
            self.network.g_session.node[node]['tags'] = tags

            prefixes = dict( (prefix, self.prefix_lists[prefix]) for prefix in data['prefixes'])
            # store updated tags
            self.network.g_session.node[node]['prefixes'] = prefixes


    def apply_bus_rel(self, query):
        result = self.br_query.parseString(query)
        if "relationshipString" in result:
            self.g_business_relationship.add_edge(result.provider, result.client, 
                    relationship = result.relationship)
        elif "serviceString" in result:
            self.g_business_relationship.add_edge(result.provider, result.client, service=result.service)
        elif "asnAlias" in result:
            asn = result.asn
            alias = result.network
            if alias in self.g_business_relationship:
                self.g_business_relationship.node[alias]['asn'] = asn
            else:
                self.g_business_relationship.add_node(alias, asn=asn)

        # Now apply business relationship policies
        #TODO: check that each node has an ASN


    def apply_gao_rexford(self):
        """ looks at business relationship graph"""
        print self.g_business_relationship.nodes(data=True)
        g_bus_rel = self.g_business_relationship
        print g_bus_rel.edges(data=True)

        def asn(node):
            return 
        for node in sorted(g_bus_rel):
            print "Node %s " % node
            node_asn = g_bus_rel.node[node].get('asn')
            neighbors = {
                    "partial transit customer": [],
                    "customer": [],
                    "peer": [],
                    "provider": [],
            }

            predecessors = (n for n in g_bus_rel.predecessors(node))
            successors = (n for n in g_bus_rel.successors(node))
# Map with relationship
            predecessors = [ (n, g_bus_rel[n][node].get('relationship')) for n in predecessors]
            successors = [ (n, g_bus_rel[node][n].get('relationship')) for n in successors]
            for neigh, rel in predecessors:
                if rel == 'partial transit customer':
                    neighbors['partial transit customer'].append(neigh)
                elif rel == 'customer':
                    neighbors['customer'].append(neigh)
                elif rel == 'peer':
                    neighbors['peer'].append(neigh)
                elif rel == 'provider':
                    neighbors['provider'].append(neigh)
            for neigh, rel in successors:
# oppposite direction
                if rel == 'partial transit customer':
                    neighbors['provider'].append(neigh)
                elif rel == 'customer':
                    neighbors['provider'].append(neigh)
                elif rel == 'peer':
                    neighbors['peer'].append(neigh)
                elif rel == 'provider':
                    neighbors['customer'].append(neigh)

            for neigh in neighbors['partial transit customer']:
                print "ptcust", neigh
                neigh_asn = g_bus_rel.node[neigh].get('asn')
		pol = "(asn = %s) ->ingress (asn = %s): addTag parttrans_tag" % (neigh_asn, node_asn)
                print pol
                self.apply_bgp_policy(pol)
		pol = "(asn = %s) egress-> (asn = %s): if tag = provider_tag then reject" % (node_asn, neigh_asn)
                print pol
                self.apply_bgp_policy(pol)
                
            for neigh in neighbors['customer']:
                neigh_asn = g_bus_rel.node[neigh].get('asn')
                print "cust", neigh
                pol = "(asn = %s) ->ingress (asn = %s): addTag provider_tag" % (neigh_asn, node_asn)
                print pol
                self.apply_bgp_policy(pol)
                pol = "(asn = %s) egress-> (asn = %s): if tag = peer_tag then reject elif tag = parttrans_tag then reject" % (node_asn, neigh_asn)
                print pol
                self.apply_bgp_policy(pol)
                
            for neigh in neighbors['peer']:
                neigh_asn = g_bus_rel.node[neigh].get('asn')
                print "peer", neigh
                pol = "(asn = %s) ->ingress (asn = %s): addTag peer_tag" % (neigh_asn, node_asn)
                print pol
                self.apply_bgp_policy(pol)
		pol = "(asn = %s) egress-> (asn = %s): if tag = provider_tag then reject" % (node_asn, neigh_asn)
                print pol
                self.apply_bgp_policy(pol)

            for neigh in neighbors['provider']:
                neigh_asn = g_bus_rel.node[neigh].get('asn')
                print "provider", neigh
		pol = "(asn = %s) ->ingress (asn = %s): addTag provider_tag" % (neigh_asn, node_asn)
                print pol
                self.apply_bgp_policy(pol)
                pol = "(asn = %s) egress-> (asn = %s): if tag = peer_tag then reject elif tag = PartTrans_tag then reject" % (node_asn, neigh_asn)
                print pol
                self.apply_bgp_policy(pol)

                

            # Now apply appropriate policies
            """
            for all neighbors:
  if neighbor=provider then:
		(provider)-->ingress(localAS):addTag Provider_tag
                (localAS)-->egress(provider):if tag=Peer_tag then reject
					     elif tag=PartTrans_tag then reject
  elif neighbor=peer then:
		(peer)-->ingress(localAS):addTag Peer_tag
		(localAS)-->egress(peer):if tag=Provider_tag then reject
  elif neighbor=partial_transit_customer then:
		(partial_transit_customer)-->ingress(localAS):addTag PartTrans_tag
		(localAS)-->egress(partial_transit_customer):if tag=Provider_tag then reject
  elif neighbor=prefer_customer then:
		(prefer_customer)-->ingress(localAS):set localPref=120
  elif neighbor=depref_me then:
		(depref_me)-->ingress(localAS):if tag=depref_me then set localPref=90
                """

    def apply_policy_file(self, policy_in_file):
        """Applies a BGP policy file to the network"""
        LOG.debug("Applying policy file %s" % policy_in_file)
        with open( policy_in_file, 'r') as f_pol:
            for line in f_pol.readlines():
                if line.startswith("#"):
                    LOG.debug("Skipping commented line %s", line)
                    continue
                if line.strip() == "":
# blank line
                    continue
                try:
                    LOG.debug("Trying policy %s" % line)
                    self.apply_bgp_policy(line)
                except:
                    raise
                    #try as business relationship query
                    try:
                        self.apply_bus_rel(line)
                    except:
                        LOG.warn("Unable to parse query line %s" % line)
        self.cl_and_pl_per_node()
        self.allocate_tags()
        self.store_tags_per_router()
        print ank.debug_edges(self.network.g_session)
        #self.apply_gao_rexford()
