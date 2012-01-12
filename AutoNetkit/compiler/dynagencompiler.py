"""
Generate dynagen configuration files for a network 
"""
from mako.lookup import TemplateLookup    

from pkg_resources import resource_filename         
import pkg_resources

import os

import logging
LOG = logging.getLogger("ANK")

import shutil      
import glob
import netaddr
import time
import tarfile

import AutoNetkit as ank
#from ank.config import config
from AutoNetkit import config
settings = config.settings          

import pprint   
pp = pprint.PrettyPrinter(indent=4)      

# Check can write to template cache directory
template_cache_dir = config.template_cache_dir

if (os.path.exists(template_cache_dir) 
    and not os.access(template_cache_dir, os.W_OK)):
    LOG.info("Unable to write to cache dir %s, "
             "template caching disabled" % template_cache_dir)
    template_cache_dir = None

template_dir =  resource_filename("AutoNetkit","lib/templates")   
lookup = TemplateLookup(directories=[ template_dir ],
                        module_directory= template_cache_dir,
                        #cache_type='memory',
                        #cache_enabled=True,
                       )
                
import os    
import itertools

#TODO: add more detailed exception handling to catch writing errors
# eg for each subdir of templates

#TODO: make this a module
#TODO: make this a netkit compiler plugin
#TODO: clear up label vs node id

#TODO: Move these into a netkit helper function*****
def lab_dir():
    #TODO: make use config
    return config.dynagen_dir

def router_conf_dir():
    #TODO: make use config
    #return config.lab_dir
    return os.path.join(lab_dir(), "configs")

def router_conf_file(network, router):
    """Returns filename for config file for router"""
    return "%s.conf" % ank.rtr_folder_name(network, router)

def router_conf_path(network, router):
    """ Returns full path to router config file"""
    r_file = router_conf_file(network, router)
    return os.path.join(router_conf_dir(), r_file)


class dynagenCompiler:  
    """Compiler main"""

    def __init__(self, network, igp, services, image, hypervisor):
        self.network = network
        self.services = services
        self.image = image
        self.hypervisor = hypervisor
        self.igp = igp
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

        if not os.path.isdir(router_conf_dir()):
            os.mkdir(router_conf_dir()) 

        return

    def configure_interfaces(self, device):
        LOG.debug("Configuring interfaces for %s" % self.network.fqdn(device))
        """Interface configuration"""
        lo_ip = self.network.lo_ip(device)
        interfaces = []

        interfaces.append({
            'id':          'lo0',
            'ip':           str(lo_ip.ip),
            'netmask':      str(lo_ip.netmask),
            'wildcard':      str(lo_ip.hostmask),
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
                'netmask':    str(subnet.netmask),
                'wildcard':      str(subnet.hostmask),
                'broadcast':    str(subnet.broadcast),
                'description':  description,
            })

        return interfaces

    def configure_igp(self, router, igp_graph, ebgp_graph):
        """igp configuration"""
        LOG.debug("Configuring IGP for %s" % self.network.label(router))
        default_weight = 1
#TODO: get area from router
        default_area = 0
        igp_interfaces = []
        if igp_graph.degree(router) > 0:
            # Only start IGP process if IGP links
#TODO: make loopback a network mask so don't have to do "0.0.0.0"
            igp_interfaces.append({ 'id': 'lo0', 'wildcard': "0.0.0.0", 'passive': True,
                'network': "255.255.255.255",
                'area': default_area, 'weight': default_weight,
                })
            for src, dst, data in igp_graph.edges(router, data=True):
                int_id = ank.junos_logical_int_id_ge(self.int_id(data['id']))
                subnet = self.network.graph[src][dst]['sn']
                description = 'Interface %s -> %s' % (
                        ank.fqdn(self.network, src), 
                        ank.fqdn(self.network, dst))
                igp_interfaces.append({
                    'id':       int_id,
                    'weight':   data.get('weight', default_weight),
                    'area':   data.get('area', default_area),
                    'network': str(subnet.network),
                    'description': description,
                    'wildcard':      str(subnet.hostmask),
                    })

# Need to add eBGP edges as passive interfaces
            for src, dst in ebgp_graph.edges(router):
# Get relevant edges from ebgp_graph, and edge data from physical graph
                data = self.network.graph[src][dst]
                int_id = ank.junos_logical_int_id_ge(self.int_id(data['id']))
                subnet = self.network.graph[src][dst]['sn']
                description = 'Interface %s -> %s' % (
                    ank.fqdn(self.network, src), 
                    ank.fqdn(self.network, dst))
                igp_interfaces.append({
                    'id':       int_id,
                    'weight':   data.get('weight', default_weight),
                    'area':   data.get('area', default_area),
                    'description': description,
                    'passive': True,
                    'network': str(subnet.network),
                    'wildcard':      str(subnet.hostmask),
                    })

        return igp_interfaces

    def configure_bgp(self, router, physical_graph, ibgp_graph, ebgp_graph):
        LOG.debug("Configuring BGP for %s" % self.network.fqdn(router))
        """ BGP configuration"""
#TODO: Don't configure iBGP or eBGP if no eBGP edges
# need to pass correct blank dicts to templates then...

#TODO: put comments in for IOS bgp peerings
        # route maps
        bgp_groups = {}
        route_maps = []
        ibgp_neighbor_list = []
        ibgp_rr_client_list = []
        route_map_call_groups = {}
        
        if router in ibgp_graph:
            for src, neigh, data in ibgp_graph.edges(router, data=True):
                route_maps_in = [route_map for route_map in 
                        self.network.g_session[neigh][router]['ingress']]
                rm_call_group_name_in = None
                if len(route_maps_in):
                    rm_call_group_name_in = "rm_call_%s_in" % self.network.fqdn(neigh).replace(".", "_")
                    route_map_call_groups[rm_call_group_name_in] = [r.name for r in route_maps_in]
                    route_maps += route_maps_in

                rm_call_group_name_out = "rm_call_%s_out" % self.network.fqdn(neigh).replace(".", "_")
                route_maps_out = [route_map for route_map in 
                        self.network.g_session[router][neigh]['egress']]
                rm_call_group_name_out = None
                if len(route_maps_out):
                    rm_call_group_name_out = "rm_call_%s_out" % (
                            self.network.fqdn(neigh).replace(".", "_"))
                    route_map_call_groups[rm_call_group_name_out] = [r.name for r in route_maps_out]
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

    def configure_ios(self):
        """ Configures IOS"""
        LOG.info("Configuring IOS")
        ios_template = lookup.get_template("cisco/ios.mako")
        ank_version = pkg_resources.get_distribution("AutoNetkit").version
        date = time.strftime("%Y-%m-%d %H:%M", time.localtime())

        physical_graph = self.network.graph
        igp_graph = ank.igp_graph(self.network)
        ibgp_graph = ank.get_ibgp_graph(self.network)
        ebgp_graph = ank.get_ebgp_graph(self.network)

        for router in self.network.routers():
            #check interfaces feasible
#TODO: make in_degree a property eg link_count
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
                f_jun.write( ios_template.render(
                    hostname = router.rtr_folder_name,
                    username = 'autonetkit',
                    interfaces=interfaces,
                    igp_interfaces=igp_interfaces,
                    igp_protocol = self.igp,
# explicit protocol
                    use_isis = self.igp == 'isis',
                    asn = asn,
                    lo_ip=lo_ip,
                    #TODO: make router have property "identifier" which maps to lo_ip
                    router_id = lo_ip.ip,
                    network_list = network_list,
                    bgp_groups = bgp_groups,
                    policy_options = policy_options,
                    ank_version = ank_version,
                    date = date,
                    ))

    
    def int_id(self, interface_id):
        #TODO: split this out
        return 'e1/%s' % interface_id
        #TODO: also allocate fast ethernet
        if interface_id == 0:
            return 'f0/0'
        if interface_id == 1:
            return 'f0/1'
        else:
            return 'e1/%s' % (interface_id - 2)

    def cisco_int_name_full(self, interface_id):
        abbrev = self.int_id(interface_id)
        abbrev =  abbrev.replace('f', 'FastEthernet ')
        abbrev =  abbrev.replace('e', 'Ethernet ')
        return abbrev

    def configure_dynagen(self):  
        """Generates dynagen specific configuration files."""
        LOG.info("Configuring Dynagen")

        # Location of IOS binary
        working_dir = "/tmp" 
        # Set up lab

        # Set up routers
        lab_template = lookup.get_template("dynagen/topology.mako")

        # Counter starting at 2000, eg 2000, 2001, 2002, etc
        console_port = itertools.count(2000)

        # also map lat/long to x,y if present


        #TODO: need nice way to map ANK graph into feasible hardware graph

        chassis = config.settings['Lab']['dynagen model']

        # Need more robust way to handle this
        # Interface mapping

        # Need to allocate Cisco interfaces

    
        # convenient alias
        graph = self.network.graph

        #TODO: basic layout if lat/long present

        all_router_info = {}

        #TODO: make this use dynagen tagged nodes
        for node in self.network.get_nodes_by_property('platform', 'NETKIT'):
            router_info = {}

            data = graph.node[node]
            hostname = ank.fqdn(self.network, node)
            router_info['hostname'] = hostname

            if 'model' in data:
                router_info['model'] = data['model'] 
            else:
                router_info['model'] = defaults['model'] 

            router_info['console'] = console_port.next() 
            #TODO: tidy this up - want relative reference to config dir
            rtr_conf_file = os.path.join("configs", "%s.cfg" % hostname)
            #router_info['cnfg'] = rtr_conf_file
            # Absolute configs for remote dynagen deployment
#TODO: make this dependent on remote host - if localhost then don't use
# and if do use, then 
            rtr_conf_file_with_path = os.path.join(lab_dir(), rtr_conf_file)
            router_info['cnfg'] = os.path.abspath(rtr_conf_file_with_path)

            # Max of 3 connections out
            # todo: check symmetric
            router_links = []

            #if graph.out_degree(node) == 2:
                # Add another card
                #router_info['slot1'] = "NM-1FE-TX"
            #TODO: use other modules
            if graph.out_degree(node) > 4:
                LOG.warning("Router %s has more than 4 interfaces, skipping" %
                            hostname)
            else:
                router_info['slot1'] = "NM-4E"
                for src, dst, data in graph.edges(node, data=True):
                    # Src is node, dst is router connected to. Link data in data
                    local_id = data['id']
                    remote_id = graph.edge[dst][src]['id']
                    local_cisco_id = cisco_int_name(local_id)
                    remote_cisco_id = cisco_int_name(remote_id)
                    remote_hostname = ank.fqdn(self.network, dst)
                    router_links.append( (local_cisco_id, remote_cisco_id,
                                          remote_hostname))

            # Store links
            router_info['links'] = router_links

            # and store info
            all_router_info[node] = router_info

        #pprint.pprint(all_router_info)
        lab_file = os.path.join(lab_dir(), "lab.net")
        with open( lab_file, 'w') as f_lab:
            f_lab.write( lab_template.render(
                image = self.image,
                hypervisor = self.hypervisor,
                all_router_info = all_router_info,   
                working_dir = working_dir,
                chassis = chassis,
                ))

        return


    def configure(self):
        self.configure_dynagen()
        self.configure_ios()
# create .tgz
        tar_filename = "dynagen_%s.tar.gz" % time.strftime("%Y%m%d_%H%M",
                time.localtime())
        tar = tarfile.open(os.path.join(config.ank_main_dir,
            tar_filename), "w:gz")
        tar.add(lab_dir())
        self.network.compiled_labs['dynagen'] = tar_filename
        tar.close()
