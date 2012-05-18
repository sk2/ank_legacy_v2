"""
Generate Netkit configuration files for a network
"""
from mako.lookup import TemplateLookup

# TODO: merge these imports but make consistent across compilers
from pkg_resources import resource_filename
import pkg_resources

import os
import networkx as nx

#import network as network

import logging
LOG = logging.getLogger("ANK")

import shutil
import glob
import itertools
from collections import namedtuple

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
    return config.libvirt_dir

def networks_dir():
    """Directory for individual Junos router configs"""
    return os.path.join(lab_dir(), "networks")

def router_conf_file(network, router):
    """Returns filename for config file for router"""
    return "%s.conf" % ank.rtr_folder_name(network, router)

def router_conf_path(network, router):
    """ Returns full path to router config file"""
    r_file = router_conf_file(network, router)
    return os.path.join(networks_dir(), r_file)

class LibvirtCompiler:
    """Compiler main"""

    def __init__(self, network, services, igp="ospf", target=None, olive_qemu_patched=False):
        self.network = network
        self.services = services
        self.igp = igp
        self.target = target
        self.olive_qemu_patched = olive_qemu_patched
        self.interface_limit = 0

#TODO: tidy up platform: Olive/Junosphere between the vmm and the device configs

     
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
        if not os.path.isdir(networks_dir()):
            os.mkdir(networks_dir())
        return

    def configure_topology(self):
        """Configure Junosphere topology structure"""
        LOG.debug("Configuring Junosphere") 
        topology_data = {}
        # Generator for private0, private1, etc
        for device in sorted(self.network.devices(), key = lambda x: x.fqdn):
            hostname = device.hostname
            print hostname
            host_file = os.path.join(lab_dir(), "%s.xml" % device.folder_name)
            with open( host_file, 'wb') as f_vmm:
                f_vmm.write("")

        for link in self.network.links():
            print link
            host_file = os.path.join(lab_dir(), "%s.xml" % device.folder_name)
            with open( host_file, 'wb') as f_vmm:
                f_vmm.write("")

        return

        for device in sorted(self.network.devices(), key = lambda x: x.fqdn):
            hostname = device.hostname
            topology_data[hostname] = {
                    'config': router_conf_file(self.network, device),
                    'interfaces': [],
                    }
            for src, dst, data in sorted(self.network.graph.edges(device, data=True), key = lambda (s,t,d): t.fqdn):
                subnet = data['sn']
                description = 'Interface %s -> %s' % (
                        ank.fqdn(self.network, src), 
                        ank.fqdn(self.network, dst))

                topology_data[hostname]['interfaces'].append({
                    'description': description,
                    })



    def configure(self):
        self.configure_topology()
# create .tgz
        tar_filename = "libvirt_%s.tar.gz" % time.strftime("%Y%m%d_%H%M",
                time.localtime())
        tar = tarfile.open(os.path.join(config.ank_main_dir,
            tar_filename), "w:gz")
        tar.add(lab_dir())
        self.network.compiled_labs['libvirt'] = tar_filename
        tar.close()
