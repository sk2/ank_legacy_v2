"""
Generate Netkit configuration files for a network
"""
from mako.lookup import TemplateLookup

from pkg_resources import resource_filename
import pkg_resources

import os

#import network as network

import logging
LOG = logging.getLogger("ANK")

import shutil
import glob
import time
import tarfile

import AutoNetkit as ank
from AutoNetkit import config
settings = config.settings

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Check can write to template cache directory
#TODO: make function to provide cache directory
template_cache_dir = config.template_cache_dir

template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
                        module_directory= template_cache_dir,
                        #cache_type='memory',
                        #cache_enabled=True,
                       )

#TODO: add more detailed exception handling to catch writing errors
# eg for each subdir of templates

#TODO: make this a module
#TODO: make this a netkit compiler plugin
#TODO: clear up label vs node id

#TODO: Move these into a netkit helper function*****
def lab_dir():
    return config.lab_dir

def netkit_dir(network, rtr):
    """Returns Netkit path"""
    #TODO: reinstate this for multi-machine ANK
    #nk_dir =  ank.netkit_hostname(network, rtr)
    #return os.path.join(lab_dir(), nk_dir)
    return lab_dir()

def shared_dir():
# Shared dir for the lab
# Refer http://wiki.netkit.org/man/man1/lstart.1.html#lbAE
    return os.path.join(lab_dir(), "shared")


def shared_etc_dir():
    return os.path.join(shared_dir(), "etc")

def router_dir(network, rtr):
    """Returns path for router rtr"""
    foldername = ank.rtr_folder_name(network, rtr)
    return os.path.join(netkit_dir(network, rtr), foldername)

def etc_dir(network, rtr):
    """Returns etc path for router rtr"""
    #TODO: rewrite these using join
    return os.path.join(router_dir(network, rtr), "etc")

def zebra_dir(network, rtr):
    """Returns formatted Zebra path"""
    return os.path.join(etc_dir(network, rtr), "zebra")

def bind_dir(network, rtr):
    """Returns bind path for router rtr"""
    return os.path.join(etc_dir(network, rtr), "bind")


class NetkitCompiler:
    """Compiler main"""

    def __init__(self, network, services, zebra_password="1234"):
        self.network = network
        self.services = services
        self.zebra_password = zebra_password
        self.interface_id = ank.netkit_interface_id
        self.tap_interface_id = ank.tap_interface_id
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

        # Create folder for netkit hosts
        #TODO: reinstate for multi-machine ANK
        if not os.path.isdir(shared_dir()):
            os.mkdir(shared_dir())
        if not os.path.isdir(shared_etc_dir()):
            os.mkdir(shared_etc_dir())
        
        if "DNS" in self.services:
            dns_list = ank.dns_list(self.network)
            dns_root = ank.root_dns(self.network)

        for node in self.network.graph:
                # Make folders - note order counts:
                # need to make router dir before zebra, etc dirs
                for test_dir in [router_dir(self.network, node),
                                 etc_dir(self.network, node),
                                 zebra_dir(self.network, node)]:
                    if not os.path.isdir(test_dir):
                        os.mkdir(test_dir)

                if "DNS" in self.services and (node in dns_list.values()
                    or node == dns_root):

                    # This router is a DNS server
                    b_dir = bind_dir(self.network, node)
                    if not os.path.isdir(b_dir):
                        os.mkdir(b_dir)
        return

    def configure_netkit(self):
        """Generates Netkit and Zebra/Quagga specific configuration files."""

        # Sets up netkit related files
        tap_host = ank.get_tap_host(self.network)

        lab_template = lookup.get_template("netkit/lab.mako")
        startup_template = lookup.get_template("netkit/startup.mako")
        zebra_daemons_template = lookup.get_template(
            "quagga/zebra_daemons.mako")
        zebra_template = lookup.get_template("quagga/zebra.mako")
        motd_template = lookup.get_template("quagga/motd.mako")

        # Shared (common) configuration
        startup_daemon_list = []
        #Setup ssh
        shutil.copy(resource_filename("AutoNetkit","lib/shadow"), shared_etc_dir())
        startup_daemon_list.append("ssh")

        f_startup = open( os.path.join(lab_dir(), "shared.startup"), 'w')
        f_startup.write(startup_template.render(
            interfaces=[],
            add_localhost=True,
            #don't send out the tap interface
            del_default_route=True,
            daemons=startup_daemon_list,
            ))
        f_startup.close()

# Files for indvidual node configuration

        #TODO: this needs to be created for each netkit host machine
        f_lab = open(os.path.join(lab_dir(), "lab.conf"), 'w')

        lab_conf = {}
        tap_list_strings = {}

        ibgp_routers = ank.ibgp_routers(self.network)
        ebgp_routers = ank.ebgp_routers(self.network)
        igp_graph = ank.igp_graph(self.network)

        if "DNS" in self.services:
            dns_list = ank.dns_list(self.network)
            #TODO-ING: generate a proper list of root DNS servers
            #TODO: replace by API call
            root_dns = ank.root_dns(self.network)

        #pprint.pprint(self.network.get_nodes_by_property('platform', 'NETKIT'))
        #pprint.pprint(list())
        #myset = self.network.q(color='red')
        #myset = list(myset)
        #print myset
        #myset = self.network.q(myset, asn='2')
        #print self.network.graph.nodes(data=True)
        #print "after filtering subset"
        #print list(myset)
        #myset = self.network.q(platform='NETKIT', color='green', area=5)
        #print list(myset)
        #myset = self.network.q(global_dns=True)
        #self.network.u(myset, ram=500)
        #pprint.pprint(self.network.graph.nodes(data=True))
        #pprint.pprint(list(self.network.q()))
        #pprint.pprint(self.network.groupby('asn'))

        for node in self.network.q(platform="NETKIT"):
            #TODO: see if rtr label is still needed, if so replace with
            # appropriate naming module function
            rtr_folder_name = ank.rtr_folder_name(self.network, node)

            lab_conf[rtr_folder_name] = []
            startup_daemon_list = ["zebra"]
            startup_int_list = []

            # convert tap list from ips into strings
            # tap_int_id cannot conflict with already allocated interfaces
            # assume edges number sequentially, so next free int id is number of
            # edges
            node_tap_id = self.tap_interface_id(self.network, node)
            tap_list_strings[rtr_folder_name] = (node_tap_id,
                                                 self.network[node].get('tap_ip'))

            if "DNS" in self.services:
                if (node in dns_list.values()) or (node == root_dns):
                    startup_daemon_list.append("bind")
                    dns_memory = 64 # Allocate more memory to DNS server 
                    #TODO: remove key, val and make it just key: val
                    lab_conf[rtr_folder_name].append( ('mem', dns_memory))

            # Zebra Daemons
            zebra_daemon_list = []
            f_zdaemons = open( os.path.join(zebra_dir(self.network, node),
                                            "daemons"), 'w')
# Always start Zebra
            zebra_daemon_list.append("zebra")

            if igp_graph.degree(node) > 0:
                zebra_daemon_list.append("ospfd") # Only start IGP process if IGP links
            if (node in ibgp_routers) or (node in ebgp_routers):
                zebra_daemon_list.append("bgpd")

            f_zdaemons.write(zebra_daemons_template.render(
                entryList = zebra_daemon_list,
            ))
            f_zdaemons.close()
# MOTD
            f_zmotd = open( os.path.join(zebra_dir(self.network, node),
                                            "motd.txt"), 'w')
            ank_version = pkg_resources.get_distribution("AutoNetkit").version
            date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
            f_zmotd.write(motd_template.render(
                date = date,
                version = ank_version,
                password = self.zebra_password,
            ))

            # Main Zebra config
            f_z = open( os.path.join(zebra_dir(self.network, node),
                                     "zebra.conf"), 'w')
            f_z.write( zebra_template.render(
                hostname = ank.fqdn(self.network, node),
                password = self.zebra_password,
                enable_password = self.zebra_password,
                use_snmp = True,
                use_debug = True,
                ))
            f_z.close()

            # Loopback interface
            lo_ip = self.network.lo_ip(node)
            startup_int_list.append({
                'int':          'lo:1',
                'ip':           str(lo_ip.ip),
                'netmask':      str(lo_ip.netmask),
            })

            # Ethernet interfaces
            for src, dst, data in self.network.graph.edges(node, data=True):
                int_id = self.interface_id(data['id'])
                subnet = data['sn']
                
                subnet = self.network.edge(src, dst).get('sn')

                # replace the / from subnet label
                collision_domain = "%s.%s" % (subnet.ip, subnet.prefixlen)
    
                # lab.conf has id in form host[0]=... for eth0 of host
                lab_conf[rtr_folder_name].append((str(data['id']), collision_domain))
                startup_int_list.append({
                    'int':          int_id,
                    'ip':           str(data['ip']),
                    'netmask':      str(subnet.netmask),
                    'broadcast':    str(subnet.broadcast),
                })

            #Write startup file for this router
            f_startup = open( os.path.join(netkit_dir(self.network, node),
                "{0}.startup".format(rtr_folder_name)), 'w')

            f_startup.write(startup_template.render(
                interfaces=startup_int_list,
                add_localhost=True,
                #don't send out the tap interface
                del_default_route=True,
                daemons=startup_daemon_list,
                ))
            f_startup.close()

        # Write lab file for whole lab
        f_lab.write(lab_template.render(
            conf = lab_conf,
            tapHost = tap_host,
            tapList = tap_list_strings,
        ))

    def configure_igp(self):
        """Generates IGP specific configuration files (eg ospfd)"""
        LOG.debug("Configuring IGP")
        template = lookup.get_template("quagga/ospf.mako")
        self.network.set_default_edge_property('weight', 1)
        netkit_routers = list(self.network.q(platform="NETKIT"))

        # configures IGP for each AS
        as_graphs = ank.get_as_graphs(self.network)
        for my_as in as_graphs:
            LOG.debug("Configuring IGP for AS {0}".format(my_as.asn))
            if my_as.number_of_edges() == 0:
                # No edges, nothing to configure
                continue

            for node in my_as:
                label = self.network.get_node_property(node, 'label')

                # Note use the AS, not the network graph for edges,
                # as only concerned with intra-AS edges for IGP
                LOG.debug("Configuring IGP for {0}".format(label))

                interface_list = []
                network_list = []

                # Add loopback info
                lo_ip = self.network.lo_ip(node)
                interface_list.append ( {'id':  "lo", 'weight':  1,
                                        'remote_router': "NA (loopback)",
                                        'remote_int': "Loopback"})
                network_list.append ( { 'cidr': lo_ip.cidr, 'ip': lo_ip.ip,
                                    'netmask': lo_ip.netmask,
                                    'area': 0, 'remote_ip': "Loopback" })
                for src, dst in my_as.edges(node):

                    int_id = self.network.get_edge_property(src, dst, 'id')
                    weight = self.network.get_edge_property(src, dst, 'weight')
                    interface_list.append ({ 'id':  'eth{0}'.format(int_id),
                                            'weight': weight,
                                            'remote_router': dst, } )

                    # fetch and format the ip details
                    subnet = self.network.get_edge_property(src, dst, 'sn')
                    local_ip = self.network.get_edge_property(src, dst, 'ip')
                    remote_ip = self.network.get_edge_property(dst, src, 'ip')
                    network_list.append ( { 'cidr': subnet.cidr, 'ip': local_ip,
                                        'netmask': subnet.netmask,
                                        'remote_ip': remote_ip, 'area': 0, } )

                #TODO: see if need to use router-id for ospfd in quagga
                if node in netkit_routers:
                    f_handle = open( os.path.join(zebra_dir(self.network, node),
                        "ospfd.conf"), 'w')
                else:
                    LOG.warn("looking at node {0}".format(my_as[node]))
                    LOG.warn("IGP not supported for device \
                        type {0}".format(my_as.node[node]["platform"]) )

                f_handle.write(template.render
                               (
                                   hostname = ank.fqdn(self.network, node),
                                   password = self.zebra_password,
                                   enable_password = self.zebra_password,
                                   interface_list = interface_list,
                                   network_list = network_list,
                                   routerID = node,
                                   use_igp = True,
                                   logfile = "/var/log/zebra/ospfd.log",
                                   use_debug = False,
                               ))

    def configure_bgp(self):
        """Generates BGP specific configuration files"""

        ip_as_allocs = ank.get_ip_as_allocs(self.network)

        LOG.debug("Configuring BGP")
        template = lookup.get_template("quagga/bgp.mako")

        route_maps = {}
        access_list = []
        communities_dict = {}

        ibgp_graph = ank.get_ibgp_graph(self.network)
        ebgp_graph = ank.get_ebgp_graph(self.network)
        physical_graph = self.network.graph

        for my_as in ank.get_as_graphs(self.network):
            LOG.debug("Configuring BGP for AS {0}".format(my_as.asn))
            # get nodes ie intersection
            #H = nx.intersection(my_as, ibgp_graph)
            # get ibgp graph that contains only nodes from this AS

            for node in my_as.nodes():
                #TODO: look at making this a set for greater comparison efficiency
                network_list = []
                route_map_call_groups = {}
                route_maps = []

                # iBGP
                ibgp_neighbor_list = []
                ibgp_rr_client_list = []
                route_reflector = False
                if node in ibgp_graph:
                    #TODO: look at replacing this with a check to len of ibgp_rr_client_list
#TODO: set cluster id explicitly from python, not auto in mako (decisions/logic in python)
                    if self.network.route_reflector(node):
                        route_reflector = True
                    for src, neigh, data in ibgp_graph.edges(node, data=True):
                        route_maps_in = [route_map for route_map in 
                                self.network.g_session[neigh][node]['ingress']]
                        rm_call_group_name_in = None
                        if len(route_maps_in):
                            rm_call_group_name_in = "rm_call_%s_in" % self.network.fqdn(neigh).replace(".", "_")
                            route_map_call_groups[rm_call_group_name_in] = [r.name for r in route_maps_in]
                            route_maps += route_maps_in

                        rm_call_group_name_out = "rm_call_%s_out" % self.network.fqdn(neigh).replace(".", "_")
                        route_maps_out = [route_map for route_map in 
                                self.network.g_session[node][neigh]['egress']]
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
                                        'remote_ip':  self.network.lo_ip(neigh).ip,
                                        'remote_router':    neigh,
                                        'description':      description,
                                        'route_map_in': rm_call_group_name_in,
                                        'route_map_out': rm_call_group_name_out,
                            })
                        elif (data.get('rr_dir') in set(['up', 'over', 'peer'])
                                or data.get('rr_dir') is None):
                            ibgp_neighbor_list.append(
                                    {
                                        'remote_ip':  self.network.lo_ip(neigh).ip,
                                        'remote_router':    neigh,
                                        'description':      description,
                                        'route_map_in': rm_call_group_name_in,
                                        'route_map_out': rm_call_group_name_out,
                                        })

                # iBGP
                ebgp_neighbor_list = []
                if node in ebgp_graph:
                    for neigh in ebgp_graph.neighbors(node):
                        route_maps_in = [route_map for route_map in 
                                self.network.g_session[neigh][node]['ingress']]
                        rm_call_group_name_in = None
                        if len(route_maps_in):
                            rm_call_group_name_in = "rm_call_%s_in" % self.network.fqdn(neigh).replace(".", "_")
                            route_map_call_groups[rm_call_group_name_in] = [r.name for r in route_maps_in]
                        route_maps += route_maps_in

                        rm_call_group_name_out = "rm_call_%s_out" % self.network.fqdn(neigh).replace(".", "_")
                        route_maps_out = [route_map for route_map in 
                                self.network.g_session[node][neigh]['egress']]
                        rm_call_group_name_out = None
                        if len(route_maps_out):
                            rm_call_group_name_out = "rm_call_%s_out" % (
                                    self.network.fqdn(neigh).replace(".", "_"))
                            route_map_call_groups[rm_call_group_name_out] = [r.name for r in route_maps_out]
                            route_maps += route_maps_out

                        description = ank.fqdn(self.network, neigh)
                        peer_ip = physical_graph[neigh][node]['ip']
                        ebgp_neighbor_list.append(
                            {
                                #'remote_ip':        neigh.lo_ip.ip  ,
                                'remote_ip': peer_ip,
                                'remote_as':        self.network.asn(neigh),
                                'remote_router':    neigh,
                                'description':      description,
                                'neigh_lo_ip':  self.network.lo_ip(neigh).ip,
                                #TODO: write function to return neighbor type
                                'neighbor_type':    "NA",
                                #TODO: write function to implement route maps
                                'route_map_in': rm_call_group_name_in,
                                'route_map_out': rm_call_group_name_out,
                            })


                adv_subnet = ip_as_allocs[self.network.asn(node)]

                # Ensure only one copy of each route map, can't use set due to list inside tuples (which won't hash)
# Use dict indexed by name, and then extract the dict items, dict hashing ensures only one route map per name
                route_maps = dict( (route_map.name, route_map) for route_map in route_maps).values()
                community_lists = {}
                prefix_lists = {}
                node_bgp_data = self.network.g_session.node.get(node)
                if node_bgp_data:
                    community_lists = node_bgp_data.get('tags')
                    prefix_lists = node_bgp_data.get('prefixes')

                # advertise this subnet
                if not adv_subnet in network_list:
# Not already listed to be advertised, advertise
                    network_list.append(adv_subnet)
                f_handle = open(os.path.join(zebra_dir(self.network, node),
                                             "bgpd.conf"),'w')

                f_handle.write(template.render(
                        hostname = ank.fqdn(self.network, node),
                        asn = self.network.asn(node),
                        password = self.zebra_password,
                        enable_password = self.zebra_password,
                        router_id = self.network.lo_ip(node).ip,
                        network_list = network_list,
                        community_lists = community_lists,
                        prefix_lists = prefix_lists,
                        #TODO: see how this differs to router_id
                        identifying_loopback = self.network.lo_ip(node),
                        ibgp_neighbor_list = ibgp_neighbor_list,
                        ebgp_neighbor_list = ebgp_neighbor_list,
                        route_reflector = route_reflector,
                        ibgp_rr_client_list = ibgp_rr_client_list,
                        route_maps = route_maps,
                        route_map_call_groups = route_map_call_groups,
                        logfile = "/var/log/zebra/bgpd.log",
                        debug=True,
                        use_debug=True,
                        dump=False,
                        snmp=False,
                ))

    def configure_dns(self):
        """Generates BIND configuration files for DNS"""
        pprint.pprint(self.network.graph.edges(data=True))
        ip_as_allocs = ank.get_ip_as_allocs(self.network)

        resolve_template = lookup.get_template("linux/resolv.mako")
        forward_template = lookup.get_template("bind/forward.mako")

        named_template = lookup.get_template("bind/named.mako")
        reverse_template = lookup.get_template("bind/reverse.mako")
        root_template = lookup.get_template("bind/root.mako")

        root_dns_template = lookup.get_template("bind/root_dns.mako")
        root_dns_named_template = lookup.get_template("bind/root_dns_named.mako")

        dns_list = ank.dns_list(self.network)

        root_dns = ank.root_dns(self.network)
        if not root_dns:
            LOG.info("No root DNS for network, skipping DNS config")
            return
        root_servers = {'name': root_dns,
                        'ip': self.network.lo_ip(root_dns).ip,
                        'hostname': ank.hostname(self.network, root_dns)}

        # Need ebgp graph to check for eBGP links allocated from this subnet
        ebgp_graph = ank.get_ebgp_graph(self.network)

        # Information for case when AS DNS server is same as Internet DNS server
        root_dns_server_entry_list = {}
        root_dns_server_domain = None

        for my_as in ank.get_as_graphs(self.network):
            asn = my_as.asn
            subnet = ip_as_allocs[asn]
            domain = ank.domain(self.network, asn)

            named_list = []
            for_entry_list = []
            #TODO: use the same list for both?
            rev_entry_list = []
            host_cname_list = []

            # Look at eBGP nodes in this subnet, the set union of nodes in both
            as_ebgp_nodes = set(my_as.nodes()) & set(ebgp_graph.nodes())
            # See if any eBGP link out of this AS uses IP from the AS subnet, if
            # so need to also add the destination for reverse DNS
            for node in as_ebgp_nodes:
                for src, dst, data in ebgp_graph.edges(node, data=True):
                    ebgp_sn = self.network.graph[src][dst]['sn']
                    if ebgp_sn in subnet:
                        # Int id and ip of link from dst (in remote AS) to src
                        int_id = ank.int_id(self.network, dst, src)
                        int_id = "eth{0}".format(int_id)
                        ip_addr = ank.ip_addr(self.network, dst, src)
                        reverse = ank.reverse_subnet(ip_addr, subnet.prefixlen)
                        # Add remote host to reverse DNS for subnet of this AS
                        rev_entry_list.append( {'int_id': int_id,
                                                'reverse': reverse,
                                                'host': ank.fqdn(self.network,
                                                                 dst)})

            #TODO: support non-classful AS subnets (base on ANKv1 code)
            if subnet.prefixlen not in [8, 16, 24]:
                LOG.warn("Only classful subnet allocations supported for DNS")
                return

            for rtr in my_as.nodes():
                hostname = ank.hostname(self.network, rtr)

                #TODO: make this a function rather than hardcoded lo0
                host_cname_list.append((hostname, "lo0.{0}".format(hostname)))
                asn = self.network.asn(rtr)

                # Obtain DNS server for this AS
                dns_server = dns_list[asn]
                dns_server_hostname = ank.hostname(self.network, dns_server)
                dns_server_ip = self.network.lo_ip(dns_server).ip

                f_resolv = open( os.path.join(etc_dir(self.network, rtr),
                                              "resolv.conf"), 'w')
                f_resolv.write ( resolve_template.render(
                    nameserver = dns_server_ip,
                    domain = ank.domain(self.network, asn) ))

                # get link data for this router
                for src, dst in self.network.get_edges(rtr):
                    int_id = ank.int_id(self.network, src, dst)
                    ip_addr = ank.ip_addr(self.network, src, dst)

                    #TODO: map int_id into eth, en, etc based on a dict
                    # skip links not belonging to this AS's subnet, eBGP links
                    if ip_addr in subnet:
                        #TODO: use a function for this
#TODO: use the platform passed into DNS, eg junosphere/olive/netkit and map the interface fn appropriately (like in junos compiler)
#TODO: this requires making the interface functions part of ank. ratehr than inside each compiler...
                        int_id = "eth{0}".format(int_id)
                        reverse = ank.reverse_subnet(ip_addr, subnet.prefixlen)
                        for_entry_list.append( {'int_id': int_id,
                                                'int_ip': str(ip_addr),
                                                'host': hostname})
                        rev_entry_list.append( {'int_id': int_id,
                                                'reverse': reverse,
                                                'host': ank.fqdn(self.network,
                                                                 rtr)})
                    else:
                        LOG.debug("Skipping link {0}.{1} as {2} "
                                  " not in {3}".format(int_id, rtr,
                                                     ip_addr, subnet))

                # and add loopbacks
                # loopback ip is a subnet, extract IP from it
                lo_subnet = self.network.lo_ip(rtr)
                #TODO: make this a universal constant
                int_id = "lo0"
                reverse = ank.reverse_subnet(lo_subnet.ip, subnet.prefixlen)

                for_entry_list.append( {'int_id': int_id,
                                        'int_ip': str(lo_subnet.ip),
                                        'host': hostname   })
                rev_entry_list.append( {'int_id': int_id,
                                        'reverse': reverse,
                                        'host': ank.fqdn(self.network, rtr) })

            # Now setup the server
            LOG.debug("DNS server for AS{0} is {1}".format(asn, dns_server))

            rtr = dns_list[asn]
            hostname = ank.hostname(self.network, rtr)

            # Check if DNS server for this AS is same as global root DNS
            if dns_list[asn] == root_dns:
                root_dns_server_entry_list = named_list
                root_dns_server_domain = domain

            # DNS server for AS
            f_root = open( os.path.join(bind_dir(self.network, rtr),
                                        "db.root"), 'w')
            f_root.write( root_template.render(
                    root_servers = root_servers,
                ))

            # needs to be in format like db.0.0.10 or db.0.10
            identifier = ank.rev_dns_identifier(subnet)

            # Store for named.conf entry
            named_entry = {'identifier': identifier,
                           'bind_dir': "/etc/bind",
                           'filename': identifier}
            #don't duplicate entries
            #TODO: tidy this up - list comprehension?
            if(named_entry not in named_list):
                named_list.append(named_entry)

            f_named = open( os.path.join(bind_dir(self.network, rtr),
                                         "named.conf"), 'w')
            f_named.write(named_template.render(
                domain = domain,
                entry_list = named_list,
                logging = True,
            ))
            f_named.close()

            # forward entries
            # eg db.AS1
            f_forward = open ( os.path.join(bind_dir(self.network, rtr),
                                            "db.{0}".format(domain)), 'w')
            f_forward.write(forward_template.render(
                domain = domain,
                        # Only concerned the DNS entries,
                        # not the subnets they belong to
                        entry_list = for_entry_list,
                        host_cname_list =  host_cname_list,
                        #entryList =[],
                        dns_server= dns_server_hostname,
                        dns_server_ip= dns_server_ip,
                ))

            # reverse entries
            f_reverse = open(os.path.join(bind_dir(self.network, rtr),
                "db.{0}".format(identifier)), 'w')

            #ToDO: look at using reverse_dns from netaddr eg ip.reverse_dns

            #TODO: fix reverse dns
            # Sort the list based on the reverse IP
#TODO: can use item getter?
            rev_entry_list.sort(key=lambda x: (x['reverse']))
            f_reverse.write(reverse_template.render(
                subnet = subnet,
                domain = domain,
                identifier = identifier,
                entry_list = rev_entry_list,
                dns_server_ip=dns_server_ip,
                dns_server= dns_server_hostname,
                dns_server_reverse_ip = dns_server_ip.reverse_dns,
                ))


        # TODO: Make sure this is not one of
        #  the AS dns servers, otherwise the configuration will overwrite each
        # other. (probably best
        #  to make sure of this in the self.network.root_dns() call

        dns_servers = []
        for asn in dns_list:
            subnet = ip_as_allocs[asn]
            identifier = ank.rev_dns_identifier(subnet)
            rtr = dns_list[asn]
            domain = ank.domain(self.network, asn)
            hostname = ank.hostname(self.network, rtr)
            dns_servers.append({"ip": self.network.lo_ip(rtr).ip,
                                "name": rtr,
                                "AS": asn,
                                "hostname" : hostname,
                                "domain": domain,
                                "reverse": identifier})

        #return
        #write the db.root for the finding the delegation servers
        # Root DB for all of networks
        f_root_db = open(os.path.join(bind_dir(self.network, root_dns),
                                      "db.root"), 'w')

        #ToDO: see if can reduce number of calls to bind_dir here
        f_root_db.write( root_dns_template.render(
                dns_servers = dns_servers,
                root_servers= root_servers,
            ))


        # and append the root config to named file, for root DNS of all domains
        # the previously written named.conf was for each domain root DNS server
        f_named = open( os.path.join(bind_dir(self.network, root_dns),
                                     "named.conf"),
                       'w')

        f_named.write(root_dns_named_template.render(
            domain = root_dns_server_domain,
            entry_list = root_dns_server_entry_list,
            logging = True,
        ))

        #TODO: build in checks eg named-checkconf named.conf
        # and named-checkzone . db.root
        return

    def configure(self):
        """Configure Netkit"""
        LOG.info("Configuring Netkit")
        self.configure_netkit()
        self.configure_igp()
        self.configure_bgp()
        self.configure_dns()

        # create .tgz
        tar_filename = "netkit_%s.tar.gz" % time.strftime("%Y%m%d_%H%M", time.localtime())
        tar = tarfile.open(os.path.join(config.ank_main_dir, tar_filename), "w:gz")
# Store using directory structure, eg ank_lab/netkit_lab/
# Note: this differs to Junos which flattens file structure
        tar.add(lab_dir())
        self.network.compiled_labs['netkit'] = tar_filename
        tar.close()

