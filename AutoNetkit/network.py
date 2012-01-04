"""
.. module:: AutoNetkit.autonetkit

.. moduleauthor:: Simon Knight

Main functions for AutoNetkit

"""
import pprint   
import AutoNetkit as ank
from itertools import groupby
from AutoNetkit import deprecated 
# NetworkX Modules
import networkx as nx   
pp = pprint.PrettyPrinter(indent=4)       

# AutoNetkit Modules
import logging
LOG = logging.getLogger("ANK")

#TODO: update docstrings now not returning graphs as using self.graph

"""TODO: use for fast node access, eg can do self.ank[n]['asn']
        #Return a dict of neighbors of node n.  Use the expression 'G[n]'. 
        def __getitem__(self, n):

also look at
    def __iter__(self):

and 
    def __contains__(self,n):

to pass through to the netx graph methods for quick access

"""

#TODO: allow direct access to the graph where possible,
# function G is reference to the graph
# with all other methods only for access subgraphs etc
# and for getting graphs by properties

# TODO: abstract eBGP etc to be subgraph by property,
# with eBGP just being split on the 'asn' property

class Network(object): 
    """ Main network containing router graph"""

    def __init__(self, physical_graph=None):
        # IP config information
        #TODO: make this a general attributes dictionary
        self.tap_host = None
        self.tap_sn = None
        self.ip_as_allocs = None

        self.as_names = {}
        self._graphs = {}
        self._graphs['physical'] = nx.DiGraph()
        if physical_graph:
            self._graphs['physical'] = physical_graph
        self._graphs['bgp_session'] = nx.DiGraph()
        self.compiled_labs = {} # Record compiled lab filenames, and configs

    @deprecated
    def update_node_type(self, default_type):
        """ Updates any node in graph that has no type set to be default_type"""
        for node, data in self.graph.nodes(data=True):
            if 'type' not in data: 
                self.graph.node[node]['type'] = default_type

    ################################################## 
    #### Initial Public API functions ###
    # these are used by plugins

    # or write functional library like in networkx function.py file

    #TODO: deprecate these in future, allow for .physical_graph property
    @property
    def graph(self):
        return self._graphs['physical']

    @graph.setter
    def graph(self, value):
        self._graphs['physical'] = value

    @property
    def g_session(self):
        return self._graphs['bgp_session']

    @g_session.setter
    def g_session(self, value):
        self._graphs['bgp_session'] = value

    @deprecated
    def get_edges(self, node=None):
        if node != None:
            # Can't use shortcut of "if node" as param node=0 would 
            # evaluate to same as None
            return self.graph.edges(node)
        else:
            return self.graph.edges()

    @deprecated
    def get_edge_count(self, node):
        return self.graph.degree(node)

    @deprecated
    def get_nodes_by_property(self, prop, value):
        return [n for n in self.graph
                if self.graph.node[n].get(prop) == value]

    def __getitem__(self, n):
        return self.graph.node.get(n)

    def edge(self, src, dst):
        return self.graph[src][dst]

    def q(self, nodes=None, **kwargs):
        if not nodes:
            nodes = self.graph.nodes_iter() # All nodes in graph

        # need to allow filter_func to access these args
        myargs = kwargs
        # also need to handle speed__gt=50 etc
        def ff(n):
            return all(self.graph.node[n].get(k) == v for k,v in
                            myargs.items())

        return (n for n in nodes if ff(n))

    def u(self, nodes, **kwargs):
        for n in nodes:
            for key, val in kwargs.items():
                self.graph.node[n][key] = val

    def groupby(self, attribute, nodes=None):
        if not nodes:
            nodes = self.graph.nodes_iter() # All nodes in graph

        def keyfunc(node):
            return self.graph.node[node][attribute]
        nodes = sorted(nodes, key=keyfunc )
        return groupby(nodes, keyfunc)
        
    def set_default_node_property(self, prop, value):
        for node, data in self.graph.nodes(data=True):
            if prop not in data:
                self.graph.node[node][prop] = value

    def get_node_property(self, node, prop):
        return self.graph.node[node][prop]

    @deprecated
    def set_default_edge_property(self, prop, value):
        #TODO: allow list of edges to be passed in
        # sets property if not already set
        for src, dst, data in self.graph.edges(data=True):
            if prop not in data:
                self.graph[src][dst][prop] = value

    @deprecated
    def set_edge_property(self, src, dest, prop, value):
        self.graph[src][dst][prop] = value

    @deprecated
    def get_edge_property(self, src, dst, prop):
        return self.graph[src][dst][prop]

    @deprecated
    def get_subgraph(self, nodes):
        return self.graph.subgraph(nodes)

    @deprecated
    def central_node(self, graph):  
        """returns first item (if multiple) central node for a given network."""
        if graph.number_of_nodes() is 1:
            # only one node in network, so this is the centre
            return graph.nodes()[0]

        if nx.is_strongly_connected(graph):   
            return nx.center(graph)[0]
        else:
            #TODO: break into connected components and find centre of largest of
            # these
            LOG.warn(("Error finding central node: "
                      "graph {0} is not fully connected").format(graph.name) )
            # Return a "random" node
            return graph.nodes()[0]

    ################################################## 
    #TODO: move these into a nodes shortcut module
    def asn(self, node):
        """ syntactic sugar for accessing asn of a node

        >>> network = ank.example_multi_as()
        >>> network.asn('1a')
        1
        >>> network.asn('2a')
        2
        >>> network.asn('3a')
        3
        
        """
        return int(self.graph.node[node].get('asn'))

    def lo_ip(self, node):
        """ syntactic sugar for accessing loopback IP of a node """
        return self.graph.node[node].get('lo_ip')

    def pop(self, node):
        """ syntactic sugar for accessing pop of a node """
        return self.graph.node[node].get('pop')

    def network(self, node):
        """ syntactic sugar for accessing network of a node """
        retval = self.graph.node[node].get('network')
        if retval:
            return retval
        else:
# try "Network"
            return self.graph.node[node].get('Network')

    def ibgp_cluster(self, node):
        """ syntactic sugar for accessing ibgp_cluster of a node """
        return self.graph.node[node].get('ibgp_cluster')

    def ibgp_level(self, node):
        """ syntactic sugar for accessing ibgp_level of a node """
#TODO: catch int cast exception
        return int(self.graph.node[node].get('ibgp_level'))

    def route_reflector(self, node):
        """ syntactic sugar for accessing if a ndoe is a route_reflector"""
        return self.graph.node[node].get('route_reflector')

    def label(self, node):
        """ syntactic sugar for accessing label of a node """
        #return ('label' for n in nodes)
        #return (self.graph.node[n]['label'] for n in nodes)
        label = self.graph.node[node].get('label')
        if label:
            return label
# no label set, return node name
        return str(node)

    def fqdn(self, node):
        """Shortcut to fqdn"""
        return ank.fqdn(self, node)


    # For dealing with BGP Sessions graphs
#TODO: expand this to work with arbitrary graphs

