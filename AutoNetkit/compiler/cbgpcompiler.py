"""
Generate Netkit configuration files for a network
"""
from mako.lookup import TemplateLookup
from pkg_resources import resource_filename
import os

#import network as network

import logging
LOG = logging.getLogger("ANK")

import shutil
import glob

import AutoNetkit as ank
from AutoNetkit import config
settings = config.settings
from collections import defaultdict

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Check can write to template cache directory
#TODO: make function to provide cache directory
#TODO: move this into config
template_cache_dir = config.template_cache_dir

template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )

def lab_dir():
    return config.cbgp_dir

def cbgp_file():
    """Returns filename for config file for cbgp lab"""
    return os.path.join(lab_dir(), "cbgp.cli")

def unidirectional(links):
# Only want (s,t) not (s,t) and (t,s)
# eg turn s<->t into s->t
# Use comparison as tie-breaker (arbitrary comparison)
    return ( (s,t) for (s,t) in links if not ( (t,s) in links and s < t))

class CbgpCompiler:
    """Compiler main"""

    def __init__(self, network, services):
        self.network = network
        self.services = services

    def initialise(self):
        """Creates lab folder structure"""
        if not os.path.isdir(lab_dir()):
            os.mkdir(lab_dir())
        else:
            for item in glob.iglob(os.path.join(lab_dir(), "*")):
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.unlink(item)
        return

    def configure(self):
        """Configure C-BGP"""
        LOG.info("Configuring C-BGP")
        self.initialise()
        default_weight = 1
        template = lookup.get_template("cbgp/cbgp.mako")
        physical_graph = self.network.graph
        igp_graph = ank.igp_graph(self.network)
        ibgp_graph = ank.get_ibgp_graph(self.network)
        ebgp_graph = ank.get_ebgp_graph(self.network)
        as_graphs = ank.get_as_graphs(self.network)
        ip_as_allocs = ank.get_ip_as_allocs(self.network) # Allocs for ebgp announcements

        physical_topology = defaultdict(dict)
        ibgp_topology = {} 
        igp_topology = {} 
        ebgp_topology = {}
        ebgp_prefixes = {}
        bgp_routers = {}

# Fast lookup of loopbacks - the unique router ID for cBGP
        loopback = dict( (n, self.network.lo_ip(n).ip) for n in physical_graph)

# Physical topology
        for as_graph in as_graphs:
            asn = as_graph.name
            physical_topology[asn]['nodes'] = [loopback[n] for n in as_graph]
            physical_topology[asn]['links'] = [ (loopback[s], loopback[t]) 
                    for (s,t) in unidirectional(as_graph.edges())]

# Interdomain links
        interdomain_links =  [ (loopback[s], loopback[t])
                for (s,t) in unidirectional(ebgp_graph.edges())]

#IGP configuration
        for as_graph in as_graphs:
            asn = as_graph.name
            igp_topology[asn] = {}
# Subgraph of IGP graph for this AS
            as_igp_graph = igp_graph.subgraph(as_graph.nodes())
            igp_topology[asn]['nodes'] = [loopback[n] for n in as_igp_graph]
            igp_topology[asn]['links'] = [ (loopback[s], loopback[t], data.get('weight', default_weight)) 
                    for (s,t,data) in (as_graph.edges(data=True))]

# iBGP configuration
#TODO: if ibgp graph is a clique then use "bgp domain 1 full-mesh" where 1 is asn
# use nx.graph_clique_number(G) and compare to size of G, if same then is a clique
# otherwise create ibgp session by session

#TODO: add support for non full-mesh (need to find documentation on this)
        for as_graph in as_graphs:
            asn = as_graph.name
            for router in as_graph:
                if not router.is_router:
                    continue
                if router not in ibgp_graph:
# likely single node AS
                    continue
                ibgp_topology[router] = []
                for peer in ibgp_graph.neighbors(router):
                    ibgp_topology[router].append(peer)
            bgp_routers[asn] = [n.lo_ip.ip for n in ank.bgp_routers(self.network)
                    if n.asn == asn]

# eBGP configuration
        for node in ebgp_graph.nodes():
            node_id = loopback[node]
            peers = []
            for peer in ebgp_graph.neighbors(node):
                peers.append( (self.network.asn(peer), loopback[peer]))
            ebgp_topology[node_id] = peers
# Prefixes to originate
            adv_subnet = ip_as_allocs[self.network.asn(node)]
            ebgp_prefixes[node_id] = adv_subnet

            #TODO: see if can just do for node in ebgp_graph ie without the .nodes() on end

        # bgp policy
        bgp_policy = {}
        for router in self.network.routers():
            router_id = (router.asn, router.lo_ip.ip)
            for peer in self.network.neighbors(router):
                if not peer.is_router:
                    continue
                peer_id = (peer.asn, peer.lo_ip.ip)
                pol_egress = self.network.g_session[router][peer]['egress']
                pol_ingress = self.network.g_session[peer][router]['ingress']
                if len(pol_ingress) or len(pol_egress):
                    try:
                        bgp_policy[router][peer] = {
                                'ingress': pol_ingress,
                                'egress': pol_egress,
                                }
                    except KeyError:
                        bgp_policy[router] = {}
                        bgp_policy[router][peer] = {
                                'ingress': pol_ingress,
                                'egress': pol_egress,
                                }

        # tags dict for mapping from tag to community value, and for prefixes
        tags = self.network.g_session.graph['tags']
        prefixes = self.network.g_session.graph['prefixes']

        with open( cbgp_file(), 'w') as f_cbgp:
                f_cbgp.write( template.render(
                   physical_topology = physical_topology,
                   interdomain_links = interdomain_links,
                   igp_topology = igp_topology,
                   ibgp_topology = ibgp_topology,
                   ebgp_topology = ebgp_topology,
                   ebgp_prefixes = ebgp_prefixes,
                   bgp_routers = bgp_routers,
                   bgp_policy = bgp_policy,
                   tags = tags,
                   prefixes = prefixes,
                   ))
