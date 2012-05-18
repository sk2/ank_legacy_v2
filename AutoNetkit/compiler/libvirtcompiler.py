"""
Generate Netkit configuration files for a network
"""
from mako.lookup import TemplateLookup

# TODO: merge these imports but make consistent across compilers
from pkg_resources import resource_filename
import pkg_resources

import os
import networkx as nx
import sys

#import network as network

import logging
LOG = logging.getLogger("ANK")

import shutil
import glob

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

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
        if not os.path.isdir(networks_dir()):
            os.mkdir(networks_dir())
        return

    def configure_topology(self):
        """Configure Libvirt topology structure"""
        LOG.debug("Configuring Libvirt") 
        default_vm = ET.parse(os.path.join(template_dir, "libvirt", "vm.xml"))
        default_collision_domain = ET.parse(os.path.join(template_dir, "libvirt", "collision_domain.xml"))
        #print ET.dump(default_vm)
        #print ET.dump(default_collision_domain)

        root = default_vm.getroot()
        for elem in root.iterfind('devices'):
            print elem.tag, elem.attrib

        elem = root.find('devices')
        print "elem", elem.tag, elem.attrib
        for elem in elem.iterfind('interface'):
            print "bb", elem.tag, elem.attrib

        for device in sorted(self.network.devices(), key = lambda x: x.fqdn):
            host_file = os.path.join(lab_dir(), "%s.xml" % device.folder_name)
            device = root.find("devices")

            interface = ET.SubElement(device, "interface", type="network")
            ET.SubElement(interface, "mac", address = "aaaaaaxda")
            ET.SubElement(interface, "source_network", address = "ank-1")
            ET.SubElement(interface, "address", type='pci', 
                    domain='0x0000', bus='0x00', slot='0x05', function='0x0')

            tree = ET.ElementTree(root)
            tree.write(host_file)

        for link in self.network.links():
            subnet = link.subnet
            collision_domain = "%s.%s" % (subnet.ip, subnet.prefixlen)
            collision_domain_file = os.path.join(networks_dir(), "%s.xml" % collision_domain)
            
        return



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
