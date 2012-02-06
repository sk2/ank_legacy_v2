"""
.. module:: AutoNetkit.autonetkit

.. moduleauthor:: Simon Knight

Main functions for AutoNetkit

"""
import pprint   
import AutoNetkit as ank
import cPickle as pickle
from itertools import groupby
from AutoNetkit import deprecated 
from collections import namedtuple

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

class DeviceNotFoundException(Exception):
    pass

#TODO: make these access network attribute directly rather than calling the network.label() etc
class device (namedtuple('node', "network, id")):
    __slots = ()

    def __repr__(self):
        return self.fqdn

    @property
    def folder_name(self):
        return ank.rtr_folder_name(self.network, self)

    @property
    def label(self):
        return self.network.label(self)

    @property
    def fqdn(self):
        return ank.naming.fqdn(self.network, self)

    @property
    def hostname(self):
        return ank.naming.hostname(self)

    @property
    def lo_ip(self):
        return self.network.lo_ip(self)

    @property
    def device_type(self):
        return self.network.device_type(self)

    @property
    def asn(self):
        return self.network.asn(self)

    @property
    def domain(self):
        return ank.domain(self)

    @property
    def dns_host_portion_only(self):
        return ank.dns_host_portion_only(self)
    
    @property
    def pop(self):
        return self.network.pop(self)

    @property
    def tap_ip(self):
        return self.network.graph.node[self].get("tap_ip")

    @property
    def dns_hostname(self):
        return ank.hostname(self)

    @property
    def device_hostname(self):
        """ Replaces . with _ to make safe for router configs"""
        return ank.rtr_folder_name(self.network, self)

    @property
    def is_router(self):
        return self.device_type == "router"

    @property
    def rtr_folder_name(self):
        return ank.rtr_folder_name(self.network, self)

    @property
    def is_server(self):
        return self.device_type == "server"

    @property
    def olive_ports(self):
        return self.network.graph.node[self].get("olive_ports")

    @property
    def igp_link_count(self):
        return self.network.igp_link_count(self)


class link_namedtuple (namedtuple('link', "network, src, dst")):
    __slots = ()
    def __repr__(self):
        return "(%s, %s)" % (self.src, self.dst)

    @property
    def id(self):
        return self.network.graph[self.src][self.dst]['id']

    @property
    def weight(self):
        return self.network.graph[self.src][self.dst].get("weight")

    @property
    def subnet(self):
        return self.network.graph[self.src][self.dst]['sn']

    @property
    def local_host(self):
        return self.src

    @property
    def remote_host(self):
        return self.dst

    @property
    def ip(self):
        return self.local_ip

    @property
    def local_ip(self):
        return self.network.graph[self.src][self.dst]['ip']

    @property
    def remote_ip(self):
        """Assume bi-directional link"""
        return self.network.graph[self.dst][self.src]['ip']

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
        self._graphs['bgp_session'].graph['tags'] = {}
        self._graphs['bgp_session'].graph['prefixes'] = {}
        self._graphs['dns'] = nx.DiGraph()
        self._graphs['dns_authoritative'] = nx.DiGraph()
        self.compiled_labs = {} # Record compiled lab filenames, and configs

    def __repr__(self):
        return "AutoNetkit network: %s nodes, %s edges" % (self.graph.number_of_nodes(), self.graph.number_of_edges())

    @deprecated
    def update_node_type(self, default_type):
        """ Updates any node in graph that has no type set to be default_type"""
        for node, data in self.graph.nodes(data=True):
            if 'type' not in data: 
                self.graph.node[node]['type'] = default_type

    # store network reference in node

#TODO: add add_device function, which auto relabels with network reference
    def instantiate_nodes(self):
        #mapping = dict( device(n, self) for n in self.graph)
        mapping = dict( (n, device(self, n)) for n in self.graph)
        nx.relabel_nodes(self.graph, mapping, copy=False)

    def add_device(self, node_id, asn=None, device_type=None, **kwargs):
        """ Adds a device to the physical graph"""
#TODO: keep internal counter of number of nodes that should be present, and compare in verification step - ie if user has added their own, possible corruption
        if not asn:
            asn = 1
#TODO: set this to debug once finished with
            LOG.info("Setting default asn=1 for added device %s" % node_id)
        if not device_type:
            device_type = 1
#TODO: set this to debug once finished with
            LOG.info("Setting default device_type='router' for added device %s" % node_id)
        node = device(self, node_id)
        self.graph.add_node(node, asn=asn, device_type=device_type, **kwargs)
# Return name for reference
        return node

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

    @property
    def g_dns(self):
        return self._graphs['dns']

    @g_dns.setter
    def g_dns(self, value):
        self._graphs['dns'] = value

    @property
    def g_dns_auth(self):
        return self._graphs['dns_authoritative']

    @g_dns_auth.setter
    def g_dns_auth(self, value):
        self._graphs['dns_authoritative'] = value

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

    def dns_servers(self):
        return ank.dns_servers(self)

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

    def neighbors(self, node):
        return self.graph.neighbors(node)


    def devices(self, asn=None):
        """return devices in a network"""
        if asn:
            return (n for n in self.graph if self.asn(n) == asn)
        else:
# return all nodes
            return self.graph.nodes_iter()


    def device_type(self, node):
        return self.graph.node[node].get("device_type")

    def routers(self, asn=None):
        """return routers in network"""
        return (n for n in self.devices(asn) if self.device_type(n) == 'router')

    def servers(self, asn=None):
        """return servers in network"""
        return (n for n in self.devices(asn) if self.device_type(n) == 'server')

    ################################################## 
    #TODO: move these into a nodes shortcut module
    def asn(self, node):
        """ syntactic sugar for accessing asn of a node

        >>> network = ank.example_multi_as()
        >>> network.asn("1a.AS1")
        1

        >>> [network.asn(node) for node in sorted(network.devices())]
        [1, 1, 1, 2, 2, 2, 2, 3]
        
        """
        #TODO: extend this automatic lookup logic
        try:
            return int(self.graph.node[node].get('asn'))
        except KeyError:
            try:
                return self.asn(self.find_device_by_fqdn(node))
            except DeviceNotFoundException:
                LOG.debug("Unable to find device %s" % node)


    def find_device_by_fqdn(self, fqdn):
        """
        Note: this is O(N) in number of nodes

        >>> network = ank.example_multi_as()
        >>> network.find_device_by_fqdn("1a.AS1")
        1a.AS1
        >>> network.find_device_by_fqdn("1a.AS4")
        Traceback (most recent call last):
        ...
        DeviceNotFoundException
        """
        try:
            return (device for device in self.devices() if device.fqdn == fqdn).next()
        except StopIteration:
            #TODO: throw DeviceNotFound exception here
            raise DeviceNotFoundException

    def lo_ip(self, node):
        """ syntactic sugar for accessing loopback IP of a node """
        return self.graph.node[node].get('lo_ip')

    def pop(self, node):
        """ syntactic sugar for accessing pop of a node """
        return self.graph.node[node].get('pop')

    def network(self, node):
        """ syntactic sugar for accessing network of a node """
        return self.graph.node[node].get('network') or self.graph.node[node].get('Network')

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
        if node in self.graph:
            return self.graph.node[node].get('label') or str(node.id)
        else:
            return [self.label(n) for n in node]

    def fqdn(self, node):
        """Shortcut to fqdn"""
        return ank.fqdn(self, node)

    # For dealing with BGP Sessions graphs
#TODO: expand this to work with arbitrary graphs
    def link_weight(self, src, dst):
        return self.graph[src][dst].get("weight")

    def interface_number(self, src, dst):
        return self.graph[src][dst].get("id")

    def int_ip(self, src, dst):
        return self.graph[src][dst].get("ip")

    def link_subnet(self, src, dst):
        return self.graph[src][dst].get("ip")

    def link(self, e):
        """ Returns a named-tuple for accessing link properties"""
        pass

    def add_link(self, src, dst):
        self.graph.add_edge(src, dst)
        self.graph.add_edge(dst, src)

    def link_count(self, node):
        # TODO: check in_degree == out_degree if not then WARN - or put into consistency check function
        return self.graph.in_degree(node)

    def igp_link_count(self, node):
        return len(list(self.igp_links(node)))

    def igp_links(self, node):
        return (link for link in self.links(node) if link.remote_host.asn == node.asn)

    def links(self, router=None, graph=None):
        if graph:
            return ( link_namedtuple(self, src, dst) for (src, dst) in graph.edges(router))
        else:
            return ( link_namedtuple(self, src, dst) for (src, dst) in self.graph.edges(router))

    def ebgp_graph(self):
        return ank.ebgp_graph(self)

    def ibgp_graph(self):
        return ank.ibgp_graph(self)

