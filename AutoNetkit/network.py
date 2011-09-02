"""
.. module:: AutoNetkit.autonetkit

.. moduleauthor:: Simon Knight

Main functions for AutoNetkit

"""
import pprint   
from itertools import groupby
import AutoNetkit as ank
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

    def __init__(self):

        # IP config information
        #TODO: make this a general attributes dictionary
        self.tap_host = None
        self.ip_as_allocs = None

        self.as_names = {}
        self._graphs = {}
        self._graphs['physical'] = nx.DiGraph()
        self._graphs['session'] = nx.DiGraph()

    #### IO Functions ###
    def save(self, filename="net_out.gml"):    
        """Write network topology to file."""
        nx.write_gml(self.graph, filename)  

    #TODO: also add pickle support

    #TODO: make sure use asn not as_id for consistency

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
        return self._graphs['session']

    @g_session.setter
    def g_session(self, value):
        self._graphs['session'] = value


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
        """ syntactic sugar for accessing asn of a node """
        try:
            return self.graph.node[node]['asn']
        except KeyError:
            return None

    def lo_ip(self, node):
        """ syntactic sugar for accessing loopback IP of a node """
        return self.graph.node[node]['lo_ip']

    def label(self, node):
        """ syntactic sugar for accessing label of a node """
        #return ('label' for n in nodes)
        #return (self.graph.node[n]['label'] for n in nodes)
        return self.graph.node[node]['label']

    # For dealing with BGP Sessions graphs
#TODO: expand this to work with arbitrary graphs

