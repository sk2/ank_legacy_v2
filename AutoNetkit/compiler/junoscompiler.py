"""
Generate Netkit configuration files for a network
"""
from mako.lookup import TemplateLookup

# TODO: merge these imports but make consistent across compilers
from pkg_resources import resource_filename
import pkg_resources

import os

#import network as network

import logging
LOG = logging.getLogger("ANK")

import shutil
import glob
import itertools

import AutoNetkit as ank
from AutoNetkit import config

import pprint
pp = pprint.PrettyPrinter(indent=4)
import tarfile
import time

# Check can write to template cache directory
#TODO: make function to provide cache directory
#TODO: move this into config
template_cache_dir = config.template_cache_dir

#TODO: use os.path.join here in lib/templates
template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )

def lab_dir():
    """Lab directory for junos configs"""
    return config.junos_dir

def router_conf_dir():
    """Directory for individual Junos router configs"""
    return os.path.join(lab_dir(), "configset")

def router_conf_file(network, router):
    """Returns filename for config file for router"""
    return "%s.conf" % ank.rtr_folder_name(network, router)

def router_conf_path(network, router):
    """ Returns full path to router config file"""
    r_file = router_conf_file(network, router)
    return os.path.join(router_conf_dir(), r_file)


class JunosCompiler:
    """Compiler main"""

    def __init__(self, network, services, igp, target, olive_qemu_patched=False):
        self.network = network
        self.services = services
        self.igp = igp
        self.target = target
        self.olive_qemu_patched = olive_qemu_patched
# easy reference to junosphere or olive

# Function mapping to get int_id, set depending on target platform
        self.int_id = ank.interface_id(target, olive_qemu_patched=olive_qemu_patched)
        self.interface_limit = 0

        self.junosphere = False
        if target in ['junosphere', 'junosphere_olive']:
            self.junosphere = True
            self.interface_limit = 32
        self.olive = False
        if target in ['olive', 'junosphere_olive']:
            self.olive = True

        if self.olive:
            self.interface_limit = 5
        if self.olive_qemu_patched:
# Patch allows 6 interfaces
            self.interface_limit = 6

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

        # Directory to put config files into
        if not os.path.isdir(router_conf_dir()):
            os.mkdir(router_conf_dir())
        return

    def configure_junosphere(self):
        """Configure Junosphere topology structure"""
        LOG.debug("Configuring Junosphere") 
        vmm_template = lookup.get_template("junos/topology_vmm.mako")
        topology_data = {}
        # Generator for private0, private1, etc
        #TODO: replace count with xrange up to limit of interfaces, eg 64 in Junosphere
        bridge_id_generator = ('private%s'%i for i in itertools.count(0))
        collision_to_bridge_mapping = {}

        for device in self.network.devices():
            hostname = ank.fqdn(self.network, device)
            topology_data[hostname] = {
                    'image': 'VJX1000_LATEST',
                    'config': router_conf_file(self.network, device),
                    'interfaces': [],
                    }
            for src, dst, data in self.network.graph.edges(device, data=True):
                subnet = data['sn']
                description = 'Interface %s -> %s' % (
                        ank.fqdn(self.network, src), 
                        ank.fqdn(self.network, dst))
# Bridge information for topology config
                if subnet in collision_to_bridge_mapping:
# Use bridge allocated for this subnet
                    bridge_id = collision_to_bridge_mapping[subnet]
                else:
# Allocate a bridge for this subnet
                    bridge_id = bridge_id_generator.next()
                    collision_to_bridge_mapping[subnet] = bridge_id

                topology_data[hostname]['interfaces'].append({
                    'description': description,
                    'id': self.int_id_em(data['id']),
                    'id_ge':  self.int_id(data['id']),
                    'bridge_id': bridge_id,
                    })

        if len(collision_to_bridge_mapping) > 64:
            LOG.warn("AutoNetkit does not currently support more"
                    " than 63 network links for Junosphere")

        vmm_file = os.path.join(lab_dir(), "topology.vmm")
        with open( vmm_file, 'w') as f_vmm:
            f_vmm.write( vmm_template.render(
                topology_data = topology_data,
                ))

    def configure_interfaces(self, device):
        LOG.debug("Configuring interfaces for %s" % self.network.fqdn(device))
        """Interface configuration"""
        lo_ip = self.network.lo_ip(device)
        interfaces = []

        interfaces.append({
            'id':          'lo0',
            'ip':           str(lo_ip.ip),
            'netmask':      str(lo_ip.netmask),
            'prefixlen':    str(lo_ip.prefixlen),
            'net_ent_title': ank.ip_to_net_ent_title(lo_ip),
            'description': 'Loopback',
        })

        for src, dst, data in self.network.graph.edges(device, data=True):
            subnet = data['sn']
            int_id = self.int_id(data['id'])
            description = 'Interface %s -> %s' % (
                    ank.fqdn(self.network, src), 
                    ank.fqdn(self.network, dst))

# Interface information for router config
            interfaces.append({
                'id':          int_id,
                'ip':           str(data['ip']),
                'prefixlen':    str(subnet.prefixlen),
                'broadcast':    str(subnet.broadcast),
                'description':  description,
            })

        return interfaces

    def configure_igp(self, router, igp_graph, ebgp_graph):
        """igp configuration"""
        LOG.debug("Configuring IGP for %s" % self.network.label(router))
        default_weight = 1
        igp_interfaces = []
        if igp_graph.degree(router) > 0:
            # Only start IGP process if IGP links
            igp_interfaces.append({ 'id': 'lo0', 'passive': True})
            for src, dst, data in igp_graph.edges(router, data=True):
                int_id = ank.junos_logical_int_id_ge(self.int_id(data['id']))
                description = 'Interface %s -> %s' % (
                    ank.fqdn(self.network, src), 
                    ank.fqdn(self.network, dst))
                igp_interfaces.append({
                    'id':       int_id,
                    'weight':   data.get('weight', default_weight),
                    'description': description,
                    })

# Need to add eBGP edges as passive interfaces
            for src, dst in ebgp_graph.edges(router):
# Get relevant edges from ebgp_graph, and edge data from physical graph
                data = self.network.graph[src][dst]
                int_id = ank.junos_logical_int_id_ge(self.int_id(data['id']))
                description = 'Interface %s -> %s' % (
                    ank.fqdn(self.network, src), 
                    ank.fqdn(self.network, dst))
                igp_interfaces.append({
                    'id':       int_id,
                    'weight':   data.get('weight', default_weight),
                    'description': description,
                    'passive': True,
                    })

        return igp_interfaces

    def configure_bgp(self, router, physical_graph, ibgp_graph, ebgp_graph):
        LOG.debug("Configuring BGP for %s" % self.network.fqdn(router))
        """ BGP configuration"""
#TODO: Don't configure iBGP or eBGP if no eBGP edges
# need to pass correct blank dicts to templates then...

#TODO: put comments in for junos bgp peerings
        # route maps
        bgp_groups = {}
        route_maps = []
        if router in ibgp_graph:
            internal_peers = []
            for peer in ibgp_graph.neighbors(router):
                route_maps_in = [route_map for route_map in 
                        self.network.g_session[peer][router]['ingress']]
                route_maps_out = [route_map for route_map in 
                        self.network.g_session[router][peer]['egress']]
                route_maps += route_maps_in
                route_maps += route_maps_out   
                internal_peers.append({
                    'id': self.network.lo_ip(peer).ip,
                    'route_maps_in': [r.name for r in route_maps_in],
                    'route_maps_out': [r.name for r in route_maps_out],
                    })
            bgp_groups['internal_peers'] = {
                    'type': 'internal',
                    'neighbors': internal_peers
                    }

        ibgp_neighbor_list = []
        ibgp_rr_client_list = []
        if router in ibgp_graph:
            for src, neigh, data in ibgp_graph.edges(router, data=True):
                route_maps_in = [route_map for route_map in 
                        self.network.g_session[neigh][router]['ingress']]
                route_maps_out = [route_map for route_map in 
                        self.network.g_session[router][neigh]['egress']]
                route_maps += route_maps_in
                route_maps += route_maps_out     
                description = data.get("rr_dir") + " to " + ank.fqdn(self.network, neigh)
                if data.get('rr_dir') == 'down':
                    ibgp_rr_client_list.append(
                            {
                                'id':  self.network.lo_ip(neigh).ip,
                                'description':      description,
                                'route_maps_in': [r.name for r in route_maps_in],
                                'route_maps_out': [r.name for r in route_maps_out],
                                })
                elif (data.get('rr_dir') in set(['up', 'over', 'peer'])
                        or data.get('rr_dir') is None):
                    ibgp_neighbor_list.append(
                            {
                                'id':  self.network.lo_ip(neigh).ip,
                                'description':      description,
                                'route_maps_in': [r.name for r in route_maps_in],
                                'route_maps_out': [r.name for r in route_maps_out],
                                })

        bgp_groups['internal_peers'] = {
            'type': 'internal',
            'neighbors': ibgp_neighbor_list
            }
        if len(ibgp_rr_client_list):
            bgp_groups['internal_rr'] = {
                    'type': 'internal',
                    'neighbors': ibgp_rr_client_list,
                    'cluster': self.network.lo_ip(router).ip,
                    }

        if router in ebgp_graph:
            external_peers = []
            for peer in ebgp_graph.neighbors(router):
                route_maps_in = [route_map for route_map in 
                        self.network.g_session[peer][router]['ingress']]
                route_maps_out = [route_map for route_map in 
                        self.network.g_session[router][peer]['egress']]
                route_maps += route_maps_in
                route_maps += route_maps_out   
                peer_ip = physical_graph[peer][router]['ip']
                external_peers.append({
                    'id': peer_ip, 
                    'route_maps_in': [r.name for r in route_maps_in],
                    'route_maps_out': [r.name for r in route_maps_out],
                    'peer_as': self.network.asn(peer)})
            bgp_groups['external_peers'] = {
                    'type': 'external', 
                    'neighbors': external_peers}

# Ensure only one copy of each route map, can't use set due to list inside tuples (which won't hash)
# Use dict indexed by name, and then extract the dict items, dict hashing ensures only one route map per name
        route_maps = dict( (route_map.name, route_map) for route_map in route_maps).values()

        community_lists = {}
        prefix_lists = {}
        node_bgp_data = self.network.g_session.node.get(router)
        if node_bgp_data:
            community_lists = node_bgp_data.get('tags')
            prefix_lists = node_bgp_data.get('prefixes')
        policy_options = {
                'community_lists': community_lists,
                'prefix_lists': prefix_lists,
                'route_maps': route_maps,
                }

        return (bgp_groups, policy_options)

    def configure_junos(self):
        """ Configures Junos"""
        LOG.info("Configuring Junos")
        junos_template = lookup.get_template("junos/junos.mako")
        ank_version = pkg_resources.get_distribution("AutoNetkit").version
        date = time.strftime("%Y-%m-%d %H:%M", time.localtime())

        physical_graph = self.network.graph
        igp_graph = ank.igp_graph(self.network)
        ibgp_graph = ank.get_ibgp_graph(self.network)
        ebgp_graph = ank.get_ebgp_graph(self.network)

        #TODO: correct this router type selector
        for router in self.network.routers():
            
            #check interfaces feasible
            if self.network.graph.in_degree(router) > self.interface_limit:
                LOG.warn("%s exceeds interface count: %s (max %s)" % (self.network.label(router),
                    self.network.graph.in_degree(router), self.interface_limit))
            asn = self.network.asn(router)
            network_list = []
            lo_ip = self.network.lo_ip(router)

            interfaces = self.configure_interfaces(router)
            igp_interfaces = self.configure_igp(router, igp_graph,ebgp_graph)
            (bgp_groups, policy_options) = self.configure_bgp(router, physical_graph, ibgp_graph, ebgp_graph)

            # advertise AS subnet
            adv_subnet = self.network.ip_as_allocs[asn]
            if not adv_subnet in network_list:
                network_list.append(adv_subnet)

            juniper_filename = router_conf_path(self.network, router)
            with open( juniper_filename, 'w') as f_jun:
                f_jun.write( junos_template.render(
                    hostname = ank.fqdn(self.network, router),
                    username = 'autonetkit',
                    interfaces=interfaces,
                    igp_interfaces=igp_interfaces,
                    igp_protocol = self.igp,
                    asn = asn,
                    lo_ip=lo_ip,
                    router_id = lo_ip.ip,
                    network_list = network_list,
                    bgp_groups = bgp_groups,
                    policy_options = policy_options,
                    ank_version = ank_version,
                    date = date,
                    ))

    def configure(self):
        if self.junosphere:
            self.configure_junosphere()
        self.configure_junos()
# create .tgz
        tar_filename = "junos_%s.tar.gz" % time.strftime("%Y%m%d_%H%M",
                time.localtime())
        tar = tarfile.open(os.path.join(config.ank_main_dir,
            tar_filename), "w:gz")
        if self.junosphere:
# Junosphere needs to have no arcname to flatten file structure
# (need to extract into same directory as the tar.gz)
            tar.add(lab_dir(), arcname="")
        else:
            tar.add(lab_dir())
        self.network.compiled_labs['junos'] = tar_filename
        tar.close()
