"""
Internet wrapper for AutoNetkit   
"""
__author__ = """\n""".join(['Simon Knight (simon.knight@adelaide.edu.au)',
                            'Hung Nguyen (hung.nguyen@adelaide.edu.au)'])
#    Copyright (C) 2009-2010 by 
#    Simon Knight  <simon.knight@adelaide.edu.au>
#    Hung Nguyen  <hung.nguyen@adelaide.edu.au>
#    All rights reserved.
#    BSD license.
#

import os

import AutoNetkit as ank
import networkx as nx
import time
import pprint
from AutoNetkit import network
import gzip
import glob

try:
    import cPickle as pickle
except ImportError:
    import pickle

from netaddr import IPNetwork

import config

import logging
LOG = logging.getLogger("ANK")

#.............................................................................
class Internet:  
    """Create Internet, loading from filename.
    
    Args:
       filename:    file to load network topology from

    Returns:
       None

    Example usage:

    >>> inet = Internet("multias") 

    """
    
    def __init__(self, filename=None, tapsn=IPNetwork("172.16.0.0/16"),
            netkit=False, cbgp=False, dynagen=False,
            junosphere=False, junosphere_olive=False, olive=False,
            policy_file=None, olive_qemu_patched=False, deploy = False,
            igp='ospf'): 
        self.network = network.Network()
# Keep track of if deploying to smarten up compiler
        self.will_deploy = deploy
        if isinstance(config.settings.get('tapsn'), str):
            # Convert to IPNetwork
            #TODO: exception handle this failing eg incorrect subnet
            tapsn = IPNetwork(config.settings.get('tapsn'))
        self.tapsn = tapsn
        self.policy_file = policy_file
        self.compile_targets = {
                'netkit': netkit,
                'cbgp': cbgp,
                'dynagen': dynagen,
                'junosphere': junosphere,
                'junosphere_olive': junosphere_olive,
                'olive': olive,
                'olive_qemu_patched': olive_qemu_patched,
                }
        if not igp:
            igp = config.settings['Lab']['igp']
        self.igp = igp
        if filename:
            self.load(filename)
        self.services = []
         
    def add_dns(self):        
        """Set compiler to configure DNS.

        Args:
           None

        Returns:
           None

        Example usage:

        >>> inet = ank.internet.Internet()
        >>> inet.add_dns() 

        """
        self.services.append("DNS")   
    
    def load(self, filename):   
        """Loads the network description from a graph file.
        Note this is done automatically if a filename is given to
        the Internet constructor.

        Args:
           filename:    The file to load from

        Returns:
           None

        Example usage:

        >>> inet = ank.internet.Internet()
        >>> inet.load("simple")
        >>> sorted(inet.network.graph.nodes())
        [RouterB.AS1, RouterA.AS1, RouterD.AS2, RouterC.AS1, RouterA.AS2, RouterA.AS3, RouterB.AS2, RouterC.AS2]

        >>> inet = ank.internet.Internet()
        >>> inet.load("singleas")
        >>> sorted(inet.network.graph.nodes())
        [1a.AS1, 1b.AS1, 1d.AS1, 1c.AS1]

        >>> inet = ank.internet.Internet()
        >>> inet.load("multias")
        >>> sorted(inet.network.graph.nodes())
        [1b.AS1, 1a.AS1, 2d.AS2, 1c.AS1, 2a.AS2, 3a.AS3, 2b.AS2, 2c.AS2]

        """
        LOG.info("Loading")
        ext = os.path.splitext(filename)[1]
        if ext == "":
            #TODO: use try/except block here
            self.network.graph = ank.load_example(filename)

#TODO: allow url to be entered, eg from zoo, if so then download the file and proceed on as normal

        elif ext == ".gml":
            # GML file from Topology Zoo
            ank.load_zoo(self.network, filename)
        elif ext == ".graphml":
            self.network.graph = ank.load_graphml(filename)
        elif ext == ".pickle":
            LOG.warn("AutoNetkit no longer supports pickle file format, please use GraphML")
        elif ext == ".yaml":
            # Legacy ANK file format
            LOG.warn("AutoNetkit no longer supports YAML file format, please use GraphML")
        else:
            LOG.warn("AutoNetkit does not support file format %s" % ext)

        #TODO: check that loaded network has at least one node, if not throw exception
        self.network.instantiate_nodes()
    
    def plot(self, matplotlib=False): 
        """Plot the network topology

        Args:
           None

        Returns:
           None

        Example usage:

        >>> inet = ank.internet.Internet()
        >>> inet.plot()

        """              
        LOG.info("Plotting")      
        matplotlib = matplotlib or config.settings['Plotting']['matplotlib']
        if matplotlib:
            ank.plot(self.network)        
        ank.jsplot(self.network)        
        ank.summarydoc(self.network)
        ank.dump_graph(self.network.graph, os.path.join(config.log_dir, "physical"))
        physical_single_edge = nx.Graph(self.network.graph)
        ank.dump_graph(physical_single_edge, os.path.join(config.log_dir, "physical_single_edge"))
        ibgp_graph = ank.get_ibgp_graph(self.network)
        ebgp_graph = ank.get_ebgp_graph(self.network)
        ank.dump_graph(ibgp_graph, os.path.join(config.log_dir, "ibgp"))
        ank.dump_graph(ebgp_graph, os.path.join(config.log_dir, "ebgp"))
        g_dns = nx.Graph(self.network.g_dns)
        ank.dump_graph(g_dns, os.path.join(config.log_dir, "dns"))
        ank.dump_graph(self.network.g_dns_auth, os.path.join(config.log_dir, "dns_auth"))
        ank.dump_identifiers(self.network, os.path.join(config.log_dir, "identifiers.txt"))


    def dump(self):
        """Dumps overlay graphs to file 

        .. note::
            
            Doesn't currently support saving graphs - NetworkX cannot save nodes/edges with dictionary attributes

        """
        with open( os.path.join(config.log_dir, "physical.txt"), 'w') as f_pol_dump:
            f_pol_dump.write(ank.debug_nodes(self.network.graph))
            f_pol_dump.write(ank.debug_edges(self.network.graph))
        #nx.write_graphml(self.network.graph, os.path.join(config.log_dir, "physical.graphml"))

        with open( os.path.join(config.log_dir, "bgp.txt"), 'w') as f_pol_dump:
            f_pol_dump.write(ank.debug_nodes(self.network.g_session))
            f_pol_dump.write(ank.debug_edges(self.network.g_session))
        #nx.write_graphml(self.network.g_session, os.path.join(config.log_dir, "bgp.graphml"))

        with open( os.path.join(config.log_dir, "dns.txt"), 'w') as f_pol_dump:
            f_pol_dump.write(ank.debug_nodes(self.network.g_dns))
            f_pol_dump.write(ank.debug_edges(self.network.g_session))
        #nx.write_graphml(self.network.g_session, os.path.join(config.log_dir, "dns.graphml"))

        with open( os.path.join(config.log_dir, "dns_auth.txt"), 'w') as f_pol_dump:
            f_pol_dump.write(ank.debug_nodes(self.network.g_dns_auth))
            f_pol_dump.write(ank.debug_edges(self.network.g_dns_auth))
        #nx.write_graphml(self.network.g_dns_auth, os.path.join(config.log_dir))
       
    def save(self, filename=None):  
        #TODO: save into ank_lab directory
        LOG.info("Saving")
        if not filename:
            filename = "autonetkit_%s.pickle" % time.strftime("%Y%m%d_%H%M%S", time.localtime())
            pickle_dir = config.pickle_dir
            filename = os.path.join(pickle_dir, filename)
        output = gzip.GzipFile(filename, 'wb')
# workaround for pickle unable to store named-tuples
        mapping = dict( (n, n.id) for n in self.network.graph)
        save_graph = nx.relabel_nodes(self.network.graph, mapping)

        pickle.dump(save_graph, output, -1)

    def restore(self, filename=None):
        #TODO: load from ank_lab directory
        if not filename:
# Look in pickle directory
            snapshots = glob.glob(config.pickle_dir + os.sep + "*.pickle")
# Most recent file from http://stackoverflow.com/q/2014554/
            if not snapshots:
                LOG.warn("No network snapshots found")
                return
            filename = max(snapshots, key=os.path.getmtime)
            filename_only = os.path.splitext(os.path.split(filename)[1])[0]
            LOG.info("Loading most recent snapshot: %s" % filename_only)
            
        LOG.info("Restoring network")
        file = gzip.GzipFile(filename, 'rb')
        self.network.graph = pickle.load(file)
# workaround for pickle, re-instantiate
        self.network.instantiate_nodes()
    
    def optimise(self):   
        """Optimise each AS within the network.

        Args:
           None

        Returns:
           None

        Example usage:

        >>> inet = ank.internet.Internet()
        >>> inet.optimise()

        """
          
        #LOG.info("Optimising")
        #self.network.optimise_igp_weights() 

    def compile(self):             
        """Compile into device configuration files.

          Args:
             None

          Returns:
             None

          Example usage:

          >>> inet = ank.internet.Internet()
          >>> inet.compile()

          >>> inet = ank.internet.Internet()
          >>> inet.compile()

          """

        #TODO: fix import order problem with doctests:
        #No handlers could be found for logger "ANK"
        LOG.info("Compiling")

        # Sanity check
        if self.network.graph.number_of_nodes() == 0:
            LOG.warn("Cannot compile empty network")
            return

        # Clean up old archives
        ank.tidy_archives()
      
        #TODO: 
        #config.get_plugin("Inv Cap").run(self.network)   
        #ank.inv_cap_weights(self.network)
        #config.get_plugin("Test").run()
        ank.initialise_bgp(self.network)
        
        # Ensure nodes have a type set
        self.network.update_node_type(default_type="netkit_router")
        ank.allocate_dns_servers(self.network)

        # Allocations  
        ank.allocate_subnets(self.network, IPNetwork("10.0.0.0/8")) 
        ank.alloc_interfaces(self.network)

        ank.alloc_tap_hosts(self.network, self.tapsn)

        if self.policy_file:
            LOG.info("Applying BGP policy from %s" % self.policy_file)
            pol_parser = ank.BgpPolicyParser(self.network)
            pol_parser.apply_policy_file(self.policy_file)
            
        if self.will_deploy and not self.compile_targets['netkit']:
            auto_compile = any( data.get("active") 
                    for data in config.settings['Netkit Hosts'].values())
            if auto_compile:
                LOG.info("Active Netkit deployment target, automatically compiling")
                self.compile_targets['netkit'] = True
        if self.compile_targets['netkit']:
            nk_comp = ank.NetkitCompiler(self.network, self.services)
            nk_comp.initialise()     
            nk_comp.configure()

        auto_compile = any( data.get("active") 
                for data in config.settings['Dynagen Hosts'].values())
        if auto_compile:
                LOG.info("Active Dynagen deployment target, automatically compiling")
                self.compile_targets['dynagen'] = True
        if self.compile_targets['dynagen']:
            dynagen_comp = ank.dynagenCompiler(self.network, services = self.services, 
                    igp = self.igp,
                    image = config.settings['Dynagen']['image'],
                    hypervisor_server = config.settings['Dynagen']['Hypervisor']['server'],
                    hypervisor_port = config.settings['Dynagen']['Hypervisor']['port'],
                    )
            dynagen_comp.initialise()     
            dynagen_comp.configure()

        if self.compile_targets['junosphere']:
            junos_comp = ank.JunosCompiler(self.network, self.services, self.igp, target="junosphere")
            junos_comp.initialise()
            junos_comp.configure()

        if self.compile_targets['junosphere_olive']:
            LOG.warn("Junosphere Olive not currently supported")
            #junos_comp = ank.JunosCompiler(self.network, self.services, self.igp, target="junosphere_olive")
            #junos_comp.initialise()
            #junos_comp.configure()

        if self.will_deploy and not self.compile_targets['olive']:
            auto_compile = any( data.get("active") 
                    for data in config.settings['Olive Hosts'].values())
            if auto_compile:
                self.compile_targets['olive'] = True
                LOG.info("Active Olive deployment target, automatically compiling")
        if self.compile_targets['olive']:
            olive_qemu_patched = self.compile_targets['olive_qemu_patched']
            junos_comp = ank.JunosCompiler(self.network, self.services, self.igp, target="olive",
                    olive_qemu_patched = olive_qemu_patched)
            junos_comp.initialise()
            junos_comp.configure()

        if self.will_deploy and not self.compile_targets['cbgp']:
            auto_compile = any( data.get("active") 
                    for data in config.settings['cBGP Hosts'].values())
            if auto_compile:
                self.compile_targets['cbgp'] = True
                LOG.info("Active cBGP deployment target, automatically compiling")
        if self.compile_targets['cbgp']:
            cbgp_comp = ank.CbgpCompiler(self.network, self.services)
            cbgp_comp.configure()


    def deploy(self):  
        """Deploy compiled configuration files."

        Args:
            None

        Returns:
           None

        Example usage:

        >>> inet = ank.internet.Internet()
        >>> inet.deploy()

        """
        for host_alias, data in config.settings['Netkit Hosts'].items():
            if not data['active']:
                LOG.debug("Not deploying inactive Netkit host %s" % host_alias)
                continue
            if not self.compile_targets['netkit']:
                LOG.info("Netkit not compiled, not deploying to host %s" % host_alias)
                continue

            # Otherwise all checks ok, deploy
            try:
                import netkit
            except ImportError:
                LOG.warn("Unable to import Netkit, ending deployment")
                return
            LOG.info("Deploying to Netkit host %s" % host_alias)   
#TODO: pass parallel count in to lstart here similar to with Olives and add to config
            netkit_server = netkit.Netkit(data['host'], data['username'],
                    tapsn=self.tapsn)

            # Get the deployment plugin
            netkit_dir = config.lab_dir
            nkd = ank.deploy.netkit_deploy.NetkitDeploy(netkit_server, netkit_dir, self.network, data['xterm'], host_alias=host_alias)
            # Need to tell deploy plugin where the netkit files are
            nkd.deploy()

        for host_alias, data in config.settings['Olive Hosts'].items():
            if not data['active']:
                LOG.debug("Not deploying inactive Olive host %s" % host_alias)
                continue

            LOG.info("Deploying to Olive host %s" % host_alias)   
            olive_deploy = ank.deploy.olive_deploy.OliveDeploy(host = data['host'],
                    username = data['username'], 
                    qemu = data['qemu'], seabios = data['seabios'],
                    host_alias = host_alias,
                    parallel = data['parallel'],
                    telnet_start_port = data['telnet start port'],
                    network = self.network, base_image = data['base image'])
            olive_deploy.deploy()
            if data['verify']:
                LOG.info("Verification not yet supported for Olive")

        for host_alias, data in config.settings['Dynagen Hosts'].items():
            if not data['active']:
                LOG.debug("Not deploying inactive Dynagen host %s" % host_alias)
                continue

            LOG.info("Deploying to Dynagen host %s" % host_alias)   
            dynagen_deploy = ank.deploy.dynagen_deploy.DynagenDeploy(host = data['host'],
                    username = data['username'], 
                    host_alias = host_alias,
                    network = self.network)
            dynagen_deploy.deploy()
            if data['verify']:
                LOG.info("Verification not yet supported for Dynagen")

        for host_alias, data in config.settings['cBGP Hosts'].items():
            if not data['active']:
                LOG.debug("Not deploying inactive cBGP host %s" % host_alias)
                continue

            LOG.info("Deploying to cBGP host %s" % host_alias)   
            cbgp_deploy = ank.deploy.cbgp_deploy.cBGPDeploy( network = self.network )
            cbgp_deploy.deploy()
            if data['verify']:
                LOG.info("Verification not yet supported for cBGP")

        return

    def collect_data(self, count=1, delay=0):
        """ Collects data for hosts"""
        LOG.info("Running collect data %s times, %s seconds between each iteration" % (count, delay))
        for collect_index in range(count):
            LOG.info("Collect iteration %s/%s" % (collect_index, count))
            collected_data_dir = config.collected_data_dir
            if not os.path.isdir(collected_data_dir):
                os.mkdir(collected_data_dir)

            for host_alias, data in config.settings['Netkit Hosts'].items():
                if not data['collect data']:
                    LOG.debug("Data collection disabled for Netkit host %s" % host_alias)
                    continue

                if not data['active']:
                    LOG.debug("Skipping data collection for inactvie Netkit host %s" % host_alias)
                    continue

                #TODO: merge netkit server and netkit deploy
                try:
                    import netkit
                except ImportError:
                    LOG.warn("Unable to import Netkit, ending deployment")
                    return

                netkit_server = netkit.Netkit(data['host'], data['username'],
                        tapsn=self.tapsn)

                # Get the deployment plugin
                netkit_dir = config.lab_dir
                nkd = ank.deploy.netkit_deploy.NetkitDeploy(netkit_server, netkit_dir, self.network, data['xterm'], host_alias=host_alias)
                # Need to tell deploy plugin where the netkit files are
                nkd.collect_data(data['collect data commands'])

            for host_alias, data in config.settings['Olive Hosts'].items():
                if not data['collect data']:
                    LOG.debug("Data collection disabled for Olive host %s" % host_alias)
                    continue

                LOG.info("Collecting data from Olive host %s" % host_alias)   
                olive_deploy = ank.deploy.olive_deploy.OliveDeploy(host = data['host'],
                        username = data['username'], 
                        parallel = data['parallel'],
                        host_alias = host_alias,
                        network = self.network )
                #TODO: get commands from config file
                olive_deploy.collect_data(data['collect data commands'])

            for host_alias, data in config.settings['cBGP Hosts'].items():
                if not data['collect data']:
                    LOG.debug("Data collection disabled for cBGP host %s" % host_alias)
                    continue

                LOG.info("Collecting data from cBGP host %s" % host_alias)   
                cbgp_deploy = ank.deploy.cbgp_deploy.cBGPDeploy( network = self.network )
                #TODO: get commands from config file
                cbgp_deploy.collect_data(data['collect data commands'])

            LOG.info("Starting collect delay of %s seconds" % delay)
            time.sleep(delay)


