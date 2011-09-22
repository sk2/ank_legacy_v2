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
import itertools

import AutoNetkit as ank
from AutoNetkit import config
settings = config.settings

import pprint
pp = pprint.PrettyPrinter(indent=4)
import tarfile
import time

# Check can write to template cache directory
#TODO: make function to provide cache directory
#TODO: move this into config
ank_dir = os.environ['HOME'] + os.sep + ".autonetkit"
if not os.path.exists(ank_dir):
    os.mkdir(ank_dir)
template_cache_dir = ank_dir + os.sep + "cache"
if not os.path.exists(template_cache_dir):
    os.mkdir(template_cache_dir)

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

def lab_dir():
    return config.junos_dir


def router_conf_dir():
    return os.path.join(lab_dir(), "configset")

def router_conf_file(network, node):
    """Returns filename for config file for router"""
    return "%s.conf"%ank.rtr_folder_name(network, node)

def router_conf_path(network, node):
    """ Returns full path to router config file"""
    r_file = router_conf_file(network, node)
    return os.path.join(router_conf_dir(), r_file)

def interface_id(numeric_id):
    """Returns Junos format interface ID for an AutoNetkit interface ID"""
# Junosphere uses em0 for external link
    numeric_id += 1
    return 'em%s' % numeric_id

class JunosCompiler:
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

        # Directory to put config files into
        if not os.path.isdir(router_conf_dir()):
            os.mkdir(router_conf_dir())
        return

    def configure_junosphere(self):
        vmm_template = lookup.get_template("junos/topology_vmm.mako")
        topology_data = {}
        # Generator for private0, private1, etc
        bridge_id_generator = ('private%s'%i for i in itertools.count(0))
        collision_to_bridge_mapping = {}

     #TODO: correct this router type selector
        for node in self.network.q(platform="NETKIT"):
            hostname = ank.fqdn(self.network, node)
            topology_data[hostname] = {
                    'image': 'VJX1000_LATEST',
                    'config': router_conf_file(self.network, node),
                    'interfaces': [],
                    }
            for src, dst, data in self.network.graph.edges(node, data=True):
                subnet = data['sn']
                int_id = interface_id(data['id'])
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
                    'id': int_id,
                    'bridge_id': bridge_id,
                    })

        if len(collision_to_bridge_mapping) > 123:
            LOG.warn("AutoNetkit does not currently support more"
                    " than 123 network links for Junosphere")

        vmm_file = os.path.join(lab_dir(), "topology.vmm")
        with open( vmm_file, 'w') as f_vmm:
            f_vmm.write( vmm_template.render(
                topology_data = topology_data,
                ))

    def configure_junos(self):
        LOG.info("Configuring Junos")
        junos_template = lookup.get_template("junos/junos.mako")

        physical_graph = self.network.graph
        igp_graph = ank.igp_graph(self.network)
        ibgp_graph = ank.get_ibgp_graph(self.network)
        ebgp_graph = ank.get_ebgp_graph(self.network)

        tap_subnet = self.network.tap_sn


        #TODO: correct this router type selector
        for node in self.network.q(platform="NETKIT"):
            hostname = ank.fqdn(self.network, node)
            asn = self.network.asn(node)
            interfaces = []
            network_list = []
            lo_ip = self.network.lo_ip(node)

            interfaces.append({
                'id':          'lo0',
                'ip':           str(lo_ip.ip),
                'netmask':      str(lo_ip.netmask),
                'prefixlen':    str(lo_ip.prefixlen),
                'description': 'Loopback',
            })

            # Add em0.0 for Qemu
            interfaces.append({
                'id':          'em0.0',
                'ip':           str(self.network[node].get('tap_ip')),
                'netmask':      str(tap_subnet.netmask),
                'prefixlen':    str(tap_subnet.prefixlen),
                'description': 'Admin for Qemu',
            })

            for src, dst, data in self.network.graph.edges(node, data=True):
                subnet = data['sn']
                int_id = interface_id(data['id'])
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

#OSPF
            ospf_interfaces = []
            if igp_graph.degree(node) > 0:
                # Only start IGP process if IGP links
                ospf_interfaces.append({ 'id': 'lo0', 'passive': True})
                for src, dst, data in igp_graph.edges(node, data=True):
                    int_id = interface_id(data['id'])
                    ospf_interfaces.append({
                        'id':          int_id,
                        })

# BGP
            adv_subnet = self.network.ip_as_allocs[asn]
            # advertise this subnet
            if not adv_subnet in network_list:
                network_list.append(adv_subnet)
            
            bgp_groups = {}
            if node in ibgp_graph:
                internal_peers = []
                for peer in ibgp_graph.neighbors(node):
                    internal_peers.append({'id': self.network.lo_ip(peer).ip})
                bgp_groups['internal_peers'] = {
                        'type': 'internal',
                        'neighbors': internal_peers
                        }

            if node in ebgp_graph:
                external_peers = []
                for peer in ebgp_graph.neighbors(node):
                    peer_ip = physical_graph[peer][node]['ip']
                    external_peers.append({
                        'id': peer_ip, 
                        'peer_as': self.network.asn(peer)})
                bgp_groups['external_peers'] = {
                        'type': 'external', 
                        'neighbors': external_peers}

            juniper_filename = router_conf_path(self.network, node)
            with open( juniper_filename, 'w') as f_jun:
                f_jun.write( junos_template.render(
                    hostname = hostname,
                    username = 'autonetkit',
                    interfaces=interfaces,
                    ospf_interfaces=ospf_interfaces,
                    asn = asn,
                    lo_ip=lo_ip,
                    router_id = lo_ip.ip,
                    network_list = network_list,
                    bgp_groups = bgp_groups,
                    ))

    def configure(self):
        self.configure_junosphere()
        self.configure_junos()
# create .tgz
        tar_filename = "junos_%s" % time.strftime("%Y%m%d_%H%M%S", time.localtime())
        tar = tarfile.open(os.path.join(config.ank_main_dir, "%s.tar.gz"%tar_filename), "w:gz")
# arcname to flatten file structure
        tar.add(lab_dir(), arcname="")
        tar.close()
