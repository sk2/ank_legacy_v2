"""
Generate dynagen configuration files for a network 
"""
from mako.lookup import TemplateLookup    

from pkg_resources import resource_filename         

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

def router_config_dir():
    #TODO: make use config
    #return config.lab_dir
    return os.path.join(lab_dir(), "configs")



class dynagenCompiler:  
    """Compiler main"""

    def __init__(self, network, services, image, hypervisor):
        self.network = network
        self.services = services
        self.image = image
        self.hypervisor = hypervisor
        # Speed improvement: grab eBGP and iBGP  graphs
        #TODO: fetch eBGP and iBGP graphs and cache them

    def initialise(self):  

        """Creates lab folder structure"""
        
        # TODO: clean out netkitdir 
        # Don't just remove the whole folder
        # Note is ok to leave lab.conf as this will be over ridden
        #TODO: make this go into one dir for each netkithost
        if not os.path.isdir(lab_dir()):
            os.mkdir(lab_dir())
        else:
            # network dir exists, clean out all (based on glob of ASxry)    
            #TODO: see if need * wildcard for standard glob
            for item in glob.iglob(os.path.join(lab_dir(), "*")):
                if os.path.isdir(item):
                    shutil.rmtree(item)           
                else:
                    os.unlink(item)

        if not os.path.isdir(router_config_dir()):
            os.mkdir(router_config_dir()) 

        return

    def configure(self):  
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

        defaults = {
            'model': 2621,

        }

        # Need more robust way to handle this
        # Interface mapping

        # Need to allocate Cisco interfaces

        def cisco_int_name(int_id):
            #TODO: split this out
            return 'e1/%s' % int_id
            #TODO: also allocate fast ethernet
            if int_id == 0:
                return 'f0/0'
            if int_id == 1:
                return 'f0/1'
            else:
                return 'e1/%s' % (int_id - 2)

        def cisco_int_name_full(int_id):
            abbrev = cisco_int_name(int_id)
            abbrev =  abbrev.replace('f', 'FastEthernet ')
            abbrev =  abbrev.replace('e', 'Ethernet ')
            return abbrev
    
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

        #TODO: Also setup chassis information

        #pprint.pprint(all_router_info)
        lab_file = os.path.join(lab_dir(), "lab.net")
        with open( lab_file, 'w') as f_lab:
            f_lab.write( lab_template.render(
                image = self.image,
                hypervisor = self.hypervisor,
                all_router_info = all_router_info,   
                working_dir = working_dir,
                ))

        # And configure the router
        cisco_template = lookup.get_template("cisco/cisco.mako") 
        self.network.set_default_edge_property('weight', 1)

        as_graphs = ank.get_as_graphs(self.network)    
        for my_as in as_graphs:  
            for node in my_as:   
                data = self.network.graph.node[node]
            
                hostname = ank.fqdn(self.network, node)
                f_cisco = open( os.path.join(router_config_dir(), 
                                            "%s.cfg" % hostname), 'w') 
                interface_list = []  
                asn = self.network.asn(node)

                # Want to setup IP for both IGP and BGP links
                for src, dst, data in graph.edges(node, data=True):
                    local_id = data['id']
                    remote_id = graph.edge[dst][src]['id']
                    subnet_cidr = data['sn'].netmask
                    local_cisco_id = cisco_int_name_full(local_id)
                    remote_cisco_id = cisco_int_name_full(remote_id)
                    remote_hostname = ank.hostname(self.network, dst)
                    interface_list.append ({
                        'id':  local_cisco_id,
                        'ip': data['ip'],
                        'sn': subnet_cidr,
                        'weight': data['weight'],
                        'remote_router': remote_hostname, 
                    } )

                igp_network_list = set() 
                all_ones = netaddr.IPAddress("255.255.255.255")
                for src, dst, data in my_as.edges(node, data=True):
                    # IGP networks
                    sn = data['sn']
                    # Want to convert eg 255.255.255.252 to 0.0.0.3
                    inv_netmask = sn.netmask ^ all_ones
                    igp_network_list.add( (sn.ip, inv_netmask) )

                
                f_cisco.write(cisco_template.render
                            (
                                hostname = hostname,
                                asn = asn,
                                password = "z",
                                image = self.image,
                                interface_list = interface_list,
                                igp_network_list = igp_network_list, 
                                logfile = "/var/log/zebra/ospfd.log",
                            ))

        # create .tgz
# create .tgz
        tar_filename = "dynagen_%s.tar.gz" % time.strftime("%Y%m%d_%H%M", time.localtime())
        tar = tarfile.open(os.path.join(config.ank_main_dir, tar_filename), "w:gz")
# arcname to flatten file structure
        tar.add(lab_dir(), arcname="dynagen_lab")
        self.network.compiled_labs['dynagen'] = tar_filename
        tar.close()
