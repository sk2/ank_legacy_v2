# -*- coding: utf-8 -*-
"""
Deploy a given Netkit lab to a Netkit server
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen, Askar Jaboldinov 

import logging
LOG = logging.getLogger("ANK")
                                 
from collections import namedtuple
                                 
import time
import os
import time
import AutoNetkit.config as config
import pxssh
import sys
import AutoNetkit as ank
import itertools
import netaddr
import random


# Used for EOF and TIMEOUT variables
import pexpect

LINUX_PROMPT = "~#"   

from mako.lookup import TemplateLookup
from pkg_resources import resource_filename

template_cache_dir = config.template_cache_dir

template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )

class OliveDeploy():  
    """ Deploy a given Junos lab to an Olive Host"""

    def __init__(self, host=None, username=None, network=None,
            lab_dir="junos_config_dir"):
        self.server = None    
        self.lab_dir = lab_dir
        self.network = network 
        self.host = host
        self.username = username
        self.shell = None
# For use on local machine
        self.shell_type ="bash"
        self.logfile = open( os.path.join(config.log_dir, "pxssh.log"), 'w')
        self.tap_name = "ank_tap_olive"
        self.vde_socket_name = "ank_vde_olive"
        self.vde_mgmt_socket_name = "ank_vde_olive_mgmt"

        self.local_server = True
        if self.host and self.username:
            # Host and Username set, so ssh will be used
            #TODO: make sure these are confirmed by the connect_server function
            self.local_server = False       


    def get_cwd(self):
        """ get current working directory"""
        # workaround for pexpect echoing the command back
        shell = self.shell
        cmd = "pwd"
        shell.sendline (cmd)  # run a command
        shell.prompt()
        result = shell.before
        result = [res.strip() for res in shell.before.split("\n")]
        if result[0] == cmd:
# First line is echo, return the next line
            return result[1]

    def connect_to_server(self):  
        """Connects to Netkit server (if remote)"""   
        
        #TODO: make internal (private) function
        
        #TODO: check state is disconnected
        
        # Connects to the Linux machine running the Netkit lab   
        shell = None     
        if self.host and self.username:  
            # Connect to remote machine

            ssh_link = self.shell
            if ssh_link != None: 
                # ssh_link already set
                return ssh_link

            shell = pxssh.pxssh()    
            shell.logfile = self.logfile
            LOG.info(  "Connecting to {0}".format(self.host) ) 

            shell.login(self.host, self.username)
            # with pass: shell.login(self.host, self.username, self.password)

            LOG.info(  "Connected to " + self.host )  
            shell.setecho(False)  
            #TODO: set state to Netkit
        else:   
            shell = pexpect.spawn (self.shell_type) 
            shell.sendline("uname")
            
            shell.logfile = self.logfile    
            shell.setecho(False)  
            # Check Linux machine (Netkit won't run on other Unixes)   
            i = shell.expect(["Linux", "Darwin", pexpect.EOF, LINUX_PROMPT]) 
            if i == 0:
                # Machine is running Linux. Send test command (ignore result)
                shell.sendline("ls") 
                shell.prompt()
            elif i == 1:
                LOG.warn("Specified Netkit host is running Mac OS X, "
                    "please specify a Linux Netkit host.")
                return None 
            else:
                LOG.warn("Provided Netkit host is not running Linux")

        self.shell = shell   
        return

    def transfer_file(self, local_file):
        """Transfers file to remote host using SCP"""
        # Sanity check
        if self.local_server:
            LOG.warn("Can only SCP to remote Netkit server")
            return

        child = pexpect.spawn("scp {0} {1}@{2}:.".format(local_file,
            self.username, self.host))      
        child.logfile = self.logfile

        child.expect(pexpect.EOF) 
        LOG.debug(  "SCP result %s"% child.before.strip())
        return 

    def unallocated_ports(self, start=11000):
        """ checks for allocated ports and returns a generator,
        which returns a free port"""
        shell = self.shell
        pattern = "tcp\s+\d\s+\d\s\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:(\d+)"
        allocated_ports = []
        netstat_command = "netstat -ant | grep LISTEN ; echo 'done'"
        shell.sendline(netstat_command)    
        for dummy in range (0, 1000):  
            i = shell.expect ([pattern, pexpect.EOF, netstat_command, 'done'])   
            if i == 0:
                port = shell.match.group(1)  
                allocated_ports.append(port)
            elif i == 1:
                break
            elif i==2:
                pass
                #netstat command echoed
            elif i==3:
                break
        return (port for port in itertools.count(start, 1) if port not in allocated_ports)

    def random_mac_addresses(self):
        """Returns a generator of random 48-bit MAC addresses"""
        return (netaddr.EUI(random.randint(1, 2**48-1), version=48)
                #TODO: see if better way to repeat the function
                for a in itertools.count(0))


    def check_required_programs(self):
        # check prerequisites
        shell = self.shell
        for program in ['tunctl', 'vde_switch', 'qemu', 'qemu-img', 'mkisofs']:
            chk_cmd = 'hash %s 2>&- && echo "Present" || echo >&2 "Absent"\n' % program
            shell.sendline(chk_cmd)
            program_installed = shell.expect (["Absent", "Present"])    
            if program_installed:
                print "%s installed" % program
            else:
                #TODO: convert print to LOGs
                print "%s not installed" % program
                return False
            shell.prompt() 



    def start_olive(self):
        """ Starts Olives inside Qemu
        Steps:
        1. Create bash script to start the Olives
        2. Copy bash script to remote host
        3. Start bash script as sudo
        """
        shell = self.shell
        print "Starting Olives"

        base_image = "/space/base-image.img"
        snapshot_folder = "/space/snapshots"
# need to create this folder if not present
        socket_folder = "/space/sockets"
        """
        required_folders = [snapshot_folder, socket_folder]
        for folder in required_folders:
            chk_cmd = '[ -d %s ] && echo "Present" "|" || echo "Absent" "|" \n\n' % folder 
            shell.sendline(chk_cmd)
            print "expecting for ", folder
            i = shell.expect (["Present |", "Absent |"])    
            print shell.before
            print shell.after
            print "got i ", i
#TODO: check if got chk_cmd back, if so was just an echo, ignore
#(need to redirect the command itself like for hash)
            if i == 0:
                print "%s doesn't exist" % folder
            elif i == 1:
                #TODO: convert print to LOGs
                print "%s  exists" % folder
            shell.prompt() 

        shell.prompt() 
        return
        """

# transfer over junos lab

        tar_file = os.path.join(config.ank_main_dir, self.network.compiled_labs['junos'])
        self.transfer_file(tar_file)
# Tar file copied across (if remote host) to local directory
        shell.sendline("cd ") 
# Remove any previous lab
        shell.sendline("rm -rf  " + self.lab_dir)
        shell.prompt() 
        shell.sendline("mkdir  " + self.lab_dir )
        shell.prompt() 

        tar_basename = os.path.basename(tar_file)
        
        # Need to force directory to extract to (junosphere format for tar extracts to cwd)
        shell.sendline("tar -xzf %s -C %s \n" % (tar_basename, self.lab_dir))

        configset_directory = os.path.join(self.lab_dir, "configset")
        print "configs are in ", configset_directory
# TODO: store these from junos compiler in network.compiled_labs dict
        config_list = []
        for node in self.network.graph.nodes():
            config_file = "%s.conf" % ank.rtr_folder_name(self.network, node)
            config_list.append(os.path.join(configset_directory, config_file))

        print config_list 
        
# make iso image

        
        return

# pass bios option (optional based on param)

# create bash script from template to start olives
        bios_image = "test.bios"
    
        unallocated_ports = self.unallocated_ports()
        mac_addresses = self.random_mac_addresses()
        qemu_routers = []

        router_info_tuple = namedtuple('route_info', 'router_name, iso_image, img_image, mac_addresses, telnet_port, switch_socket, monitor_socket')

        iso_image = "tst.iso"
        img_image = "tst.img"
        monitor_socket = "test.socket"
        

        for router in self.network.graph:
            router_info = router_info_tuple(
                    self.network.label(router),
                    iso_image,
                    img_image,
# create 6 mac addresses, the maximum per Olive
                    [mac_addresses.next() for i in range(0,6)],
                    unallocated_ports.next(),
                    self.vde_socket_name,
                    monitor_socket,
                    )
            qemu_routers.append(router_info)




        bash_template = lookup.get_template("autonetkit/olive_startup.mako")
        junos_dir = config.junos_dir
        if not os.path.isdir(junos_dir):
            os.mkdir(junos_dir)
        bash_script_filename = os.path.join(junos_dir, "start_olive.sh")
        with open( bash_script_filename, 'w') as f_bash:
            f_bash.write( bash_template.render(
                routers = qemu_routers,
                ))
        
    def start_switch(self):
        shell = self.shell

        print "Please enter sudo password and type '^]' to return to AutoNetkit"
        shell.sendline('sudo tunctl -t %s' % self.tap_name)
	sys.stdout.write (shell.after)
	sys.stdout.flush()
        shell.interact()
        print
        print "Starting vde_switch"

# start vde switch
        start_vde_switch_cmd = "vde_switch -d -t %s -n 2000 -s /tmp/%s -M /tmp/%s" % (self.tap_name, 
                self.vde_socket_name, self.vde_mgmt_socket_name)
        shell.sendline('sudo %s' % start_vde_switch_cmd)
        i = shell.expect ([ "Address already in use" , pexpect.EOF])
        if i:
# started ok
            pass
        else:
            print "WARNING: vde_switch already running"

        return






inet = ank.internet.Internet()
inet.load("singleas")
ank.alloc_interfaces(inet.network)
ank.allocate_subnets(inet.network) 
junos_comp = ank.JunosCompiler(inet.network, inet.services, inet.igp)
junos_comp.initialise()
junos_comp.configure()

olive_deploy = OliveDeploy(host="trc1", username="sknight", network=inet.network)
olive_deploy.connect_to_server()
#olive_deploy.check_required_programs()
#olive_deploy.start_switch()
olive_deploy.start_olive()

