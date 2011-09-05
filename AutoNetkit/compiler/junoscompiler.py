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

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Check can write to template cache directory
#TODO: make function to provide cache directory
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

def router_dir(network, rtr):
    """Returns path for router rtr"""
    foldername = ank.rtr_folder_name(network, rtr)
    return os.path.join(lab_dir(), foldername)

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

        for node in self.network.get_nodes_by_property('platform', 'NETKIT'):
                if not os.path.isdir(router_dir(self.network, node)):
                    os.mkdir(router_dir(self.network, node))
        return

    def configure(self):
        #TODO: Configure .vmm file also

# Configure individual routers
        LOG.info("Configuring Junos")
        junos_template = lookup.get_template("junos/junos.mako")

        physical_graph = self.network.graph
        igp_graph = ank.igp_graph(self.network)
        ibgp_graph = ank.get_ibgp_graph(self.network)
        ebgp_graph = ank.get_ebgp_graph(self.network)

        #TODO: correct this router type selector
        for node in self.network.q(platform="NETKIT"):
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

            for src, dst, data in self.network.graph.edges(node, data=True):
                subnet = data['sn']
                interfaces.append({
                    'id':          'em%s' % data['id'],
                    'ip':           str(data['ip']),
                    'prefixlen':    str(subnet.prefixlen),
                    'broadcast':    str(subnet.broadcast),
                    'description':  'Interface %s -> %s' % (
                        ank.fqdn(self.network, src), 
                        ank.fqdn(self.network, dst)),
                })

#OSPF
            ospf_interfaces = []
            ospf_interfaces.append({ 'id': 'lo0', 'passive': True})
            for src, dst, data in igp_graph.edges(node, data=True):
                ospf_interfaces.append({
                    'id':          'em%s.0' % data['id'],
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
                        'neighbors': internal_peers}

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

            juniper_filename = os.path.join(router_dir(self.network, node), "juniper.conf")
            with open( juniper_filename, 'w') as f_jun:
                f_jun.write( junos_template.render(
                    hostname = ank.fqdn(self.network, node),
                    username = 'autonetkit',
                    interfaces=interfaces,
                    ospf_interfaces=ospf_interfaces,
                    asn = asn,
                    lo_ip=lo_ip,
                    router_id = lo_ip.ip,
                    network_list = network_list,
                    bgp_groups = bgp_groups,
                    ))

