"""
Generate Libvirt configuration files for a network

Example deployment:

|-- networks
|    |- net-1.xml
|    |- net-2.xml
|    |- net-3.xml
|-- scripts
|    |- create.sh
|    |- destroy.sh
|    |- start.sh
|-- vms
     |- vm-name1
     |   -- files-for-iso
     |   -- name1.xml
     |- vm-name2
     |   -- files-for-iso
     |   -- name2.xml

"""
from mako.lookup import TemplateLookup
from mako.template import Template


# TODO: merge these imports but make consistent across compilers
import fnmatch
from pkg_resources import resource_filename
import pkg_resources
from collections import defaultdict

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

class LibvirtCompiler:
    """Compiler main"""

    def __init__(self, network, services, host, file_structure, images, script_data):
        self.network = network
        self.services = services
        self.host = host
        self.file_structure = file_structure
        self.images = images
        self.script_data = script_data

    def libvirt_dir(self):
        return config.libvirt_dir

    def lab_dir(self):
        """Lab directory for libvirt configs"""
        return os.path.join(self.libvirt_dir(), self.host)

    def networks_dir(self):
        """Directory for individual libvirt router configs"""
        return os.path.join(self.lab_dir(), "networks")

    def vm_base_dir(self):
        return os.path.join(self.lab_dir(), "vms")

#TODO: create named tuple to wrap around these, extending device to handle these cases for better programatic access
    def vm_dir(self, vm):
        return os.path.join(self.vm_base_dir(), vm.label)

    def router_conf_file(network, router):
        """Returns filename for config file for router"""
        return "%s.conf" % ank.rtr_folder_name(network, router)

    def router_conf_path(self, network, router):
        """ Returns full path to router config file"""
        r_file = self.router_conf_file(network, router)
        return os.path.join(self.networks_dir(), r_file)

    def get_collision_domain_id(self, link):
        """Returns formatted collision domain for a link"""
        return "%s.%s" % (link.subnet.ip, link.subnet.prefixlen)

    def vm_disk(self, vm):
        return "%s_%s.disk" % (vm.folder_name, vm.vm_type)

    def vm_iso(self, vm):
        return "%s_%s.iso" % (vm.folder_name, vm.vm_type)

    def vm_xml(self, vm):
        return "%s.xml" % vm.folder_name
        
    def initialise(self):
        """Creates lab folder structure"""
        if not os.path.isdir(self.libvirt_dir()):
            os.mkdir(self.libvirt_dir())
        if not os.path.isdir(self.lab_dir()):
            #TODO: this needs to split the dir up into components
            os.mkdir(self.lab_dir())
        else:
            for item in glob.iglob(os.path.join(self.lab_dir(), "*")):
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.unlink(item)

        # Directory to put config files into
        if not os.path.isdir(self.networks_dir()):
            os.mkdir(self.networks_dir())
        if not os.path.isdir(self.vm_base_dir()):
            os.mkdir(self.vm_base_dir())
        return

    def configure_topology(self):
        """Configure Libvirt topology structure"""
        #pprint.pprint( self.network.graph.nodes(data=True))
        LOG.debug("Configuring Libvirt") 
        default_vm = ET.parse(os.path.join(template_dir, "libvirt", "vm.xml"))

        fs_location = os.path.abspath(self.file_structure.get("location"))
        try:
            fs_dirs = [ os.path.join(fs_location, name) for name in os.listdir(fs_location)]
            fs_dirs = {}
            for name in os.listdir(fs_location):
                full_name = os.path.join(fs_location, name)
                if os.path.isdir(full_name):
                    fs_dirs[name] = full_name
        except OSError:
            LOG.warn("Unable to find libvirt fs: %s. Does the folder exist?" % fs_location)
            return

        LOG.debug("Locating mako templates inside fs")
# walk the fs dirs, find any mako files
        fs_mako_templates = defaultdict(list)
        for fs_dir, fs_dir_path in fs_dirs.items():
            fs_root = os.path.join(fs_location, fs_dir_path)
            for root, dirnames, filenames in os.walk(fs_dir_path):
                for filename in fnmatch.filter(filenames, '*.mako'):
                    rel_root = os.path.relpath(root, fs_root) # relative to fs root
# strip off the fs_dir
                    fs_mako_templates[fs_dir].append(os.path.join(rel_root, filename))

#TODO: batch load these templates/cache in memory for speed
# use template lookup: set at base fs dir?
        mako_tmp_dir = '/tmp/mako_modules'

# set default vm type
        default_vm_type = self.file_structure['default']
        for device in self.network:
            if not device.vm_type:
                device.vm_type = default_vm_type

        # check vm types all exist
        LOG.debug("Checking VM types have fs")
        vm_types = set(device.vm_type for device in self.network)
        if not vm_types.issubset(fs_dirs):
            missing_vms = vm_types - set(fs_dirs)
            LOG.warn("No VMs exist in fs for vms: %s" % ", ".join(missing_vms))
            return

        vms = [device for device in self.network] #TODO: filter this based on vm attribute

        for device in vms:
            vm_dir = self.vm_dir(device)

            LOG.debug("Copying fs %s for vm %s" % (device.vm_type, device))
            shutil.copytree(fs_dirs[device.vm_type], vm_dir, 
                    ignore=shutil.ignore_patterns('*.mako'))
# now use templates
            LOG.debug("Applying templates for vm %s" % str(device))
            templates = fs_mako_templates[device.vm_type]
            for template_file in templates:
                template_file = os.path.normpath(os.path.join(fs_location, device.vm_type, template_file))
                mytemplate = Template(filename=template_file, module_directory= mako_tmp_dir)
                dst_file = os.path.normpath((os.path.join(vm_dir, template_file)))
                dst_file, _ = os.path.splitext(dst_file)
                with open( dst_file, 'wb') as dst_fh:
                    dst_fh.write(mytemplate.render(
                        device = device,
                        network = self.network,
                        ))
                
# strip out mako extension
        vm_xml_files = []
        deployment_image_folder = self.images['deployment']
        source_image_folder = self.images['source']
        for device in vms:
            root = default_vm.getroot()
            host_file = os.path.join(self.lab_dir(), self.vm_xml(device))
            vm_xml_files.append(host_file)
            root.find("name").text = device.hostname
            root.find("devices/disk[@device='disk']/source").set('file', 
                    os.path.join(deployment_image_folder, self.vm_disk(device)))
            root.find("devices/disk[@device='cdrom']/source").set('file', 
                    os.path.join(deployment_image_folder, self.vm_iso(device)))

            for link in self.network.links(device):
                collision_domain = self.get_collision_domain_id(link)
                device = root.find("devices")
                interface = ET.SubElement(device, "interface", type="network")
                ET.SubElement(interface, "mac", address = "aaaaaaxda")
                ET.SubElement(interface, "model", type = "e1000")
                ET.SubElement(interface, "source", network = collision_domain)
                ET.SubElement(interface, "address", type='pci', 
                        domain='0x0000', bus='0x00', slot='0x05', function='0x0')

            tree = ET.ElementTree(root)
            tree.write(host_file)

        collision_domain_xml_files = []
        for link in self.network.links():
            collision_domain = self.get_collision_domain_id(link)
            collision_domain_file = os.path.join(self.networks_dir(), "%s.xml" % collision_domain)
            collision_domain_xml_files.append(collision_domain_file)
            elem_network = ET.Element("network")
            ET.SubElement(elem_network, "name").text = collision_domain
            ET.SubElement(elem_network, "uuid").text="aa"
            ET.SubElement(elem_network, "bridge", name = "e1000", stp="off", delay="0")
            ET.SubElement(elem_network, "mac", address = "e1000")
            tree = ET.ElementTree(elem_network)
            tree.write(collision_domain_file)

        LOG.info("Creating create script")
        template_file = os.path.join(self.script_data['base dir'], self.script_data['Create']['location'])
        mytemplate = Template(filename=template_file, module_directory= mako_tmp_dir)
#TODO: use named_tuples here instead
        vm_info = []
        for vm in vms:
            vm_info.append({
                    'type': vm.vm_type,
                    'disk': self.vm_disk(vm),
                    'iso': self.vm_iso(vm),
                    'xml': self.vm_xml(vm),
                    })

        dst_file, _ = os.path.splitext(self.script_data['Create']['location'])
        dst_file = os.path.join(self.lab_dir(), dst_file)
        with open( dst_file, 'wb') as dst_fh:
            dst_fh.write(mytemplate.render(
                vm_info = vm_info,
                source_image_folder = source_image_folder,
                deployment_image_folder = deployment_image_folder,
                **self.script_data['Create']) # pass in user defined variables
                )
        #print command

        LOG.info("Creating start script")
        template_file = os.path.join(self.script_data['base dir'], self.script_data['Start']['location'])
        mytemplate = Template(filename=template_file, module_directory= mako_tmp_dir)
        #print mytemplate.render()
        dst_file, _ = os.path.splitext(self.script_data['Start']['location'])
        dst_file = os.path.join(self.lab_dir(), dst_file)
        with open( dst_file, 'wb') as dst_fh:
            dst_fh.write(mytemplate.render(
                vm_xml_files = vm_xml_files,
                collision_domain_files = collision_domain_xml_files,
                **self.script_data['Start']) # pass in user defined variables
                )

        LOG.info("Creating destroy script")
        template_file = os.path.join(self.script_data['base dir'], self.script_data['Destroy']['location'])
        mytemplate = Template(filename=template_file, module_directory= mako_tmp_dir)
        #print mytemplate.render()
        dst_file, _ = os.path.splitext(self.script_data['Destroy']['location'])
        dst_file = os.path.join(self.lab_dir(), dst_file)
        with open( dst_file, 'wb') as dst_fh:
            dst_fh.write(mytemplate.render(
                vm_xml_files = vm_xml_files,
                collision_domain_files = collision_domain_xml_files,
                **self.script_data['Destroy']) # pass in user defined variables
                )
        #result = os.system(command)
#TODO: write to tarball directory

    def configure(self):
        self.configure_topology()
# create .tgz
        tar_filename = "libvirt_%s_%s.tar.gz" % (self.host, time.strftime("%Y%m%d_%H%M",
                time.localtime()))
        tar = tarfile.open(os.path.join(config.libvirt_dir, tar_filename), "w:gz")
        tar.add(self.lab_dir())
        try:
            self.network.compiled_labs['libvirt'][self.host] = tar_filename
        except KeyError:
            #TODO: use default dict in Internet module
            self.network.compiled_labs['libvirt'] = {}
            self.network.compiled_labs['libvirt'][self.host] = tar_filename
        tar.close()
