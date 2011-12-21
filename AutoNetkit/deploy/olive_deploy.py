# -*- coding: utf-8 -*-
"""
Deploy a given Olive lab to an Olive server
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen, Askar Jaboldinov 

import logging
LOG = logging.getLogger("ANK")
                                 
from collections import namedtuple
                                 
import os
import time
import AutoNetkit.config as config
import pxssh
import sys
import AutoNetkit as ank
import itertools
import pprint
import netaddr


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
            base_image = None,
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
        self.tap_name_base = "ank_tap_olive"
        self.vde_socket_name = None
        self.vde_mgmt_socket_name = None
        self.base_image = base_image
        self.olive_foldername = "ank_olive"

        self.local_server = True
        if self.host and self.username:
            # Host and Username set, so ssh will be used
            #TODO: make sure these are confirmed by the connect_server function
            self.local_server = False       

    def get_cwd(self):
        return self.get_command_output("pwd")

    def get_whoami(self):
        return self.get_command_output("whoami")

    def get_command_output(self, cmd):
        """ get current working directory"""
        # workaround for pexpect echoing the command back
        shell = self.shell
        shell.sendline(cmd)  # run a command
        shell.prompt()
        result = shell.before
        result = [res.strip() for res in shell.before.split("\n")]
        if result[0] == cmd:
# First line is echo, return the next line
            return result[1]

    def connect_to_server(self):  
        """Connects to Netkit server (if remote)"""   
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
        self.working_directory = self.get_cwd()
        self.linux_username = self.get_whoami()
        return True

    def transfer_file(self, local_file, remote_folder):
        """Transfers file to remote host using SCP"""
        # Sanity check
        if self.local_server:
            LOG.warn("Can only SCP to remote Netkit server")
            return

        child = pexpect.spawn("scp %s %s@%s:%s" % (local_file,
            self.username, self.host, remote_folder))      
        child.logfile = self.logfile

        child.expect(pexpect.EOF) 
        LOG.debug(  "SCP result %s"% child.before.strip())
        return 

    def unallocated_ports(self, start=11000):
        """ checks for allocated ports and returns a generator,
        which returns a free port"""
        shell = self.shell
        pattern = "tcp\s+\d\s+\d\s\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:(\d+)"
        allocated_ports = set()
        netstat_command = "netstat -ant | grep LISTEN ; echo 'done'"
        shell.sendline(netstat_command)    
        for dummy in range (0, 1000):  
            i = shell.expect ([pattern, pexpect.EOF, netstat_command, 'done'])   
            if i == 0:
                port = shell.match.group(1)  
                allocated_ports.add(int(port))
            elif i == 1:
                break
            elif i==2:
                pass
                #netstat command echoed
            elif i==3:
                break
        return (port for port in itertools.count(start, 1) if port not in allocated_ports)

    def mac_address_list(self, router_id, count):
        """Returns a generator of random 48-bit MAC addresses"""
# integer representation of '00:11:22:fe:00:00
        oui = 73601515000 + router_id*(2**8)
        return [netaddr.EUI(oui+ei, version=48, dialect=netaddr.mac_unix)
                #TODO: see if better way to repeat the function
                for ei in range(0,count)]

    def check_required_programs(self):
        shell = self.shell
        for program in ['tunctl', 'vde_switch', 'qemu', 'qemu-img', 'mkisofs']:
            chk_cmd = 'hash %s 2>&- && echo "Present" || echo >&2 "Absent"n' % program
            shell.sendline(chk_cmd)
            program_installed = shell.expect (["Absent", "Present"])    
            if program_installed:
                LOG.debug( "Required program %s installed" % program)
            else:
                LOG.info( "Required program %s not installed" % program)
                return False
            shell.prompt() 

    def create_folders(self):
        shell = self.shell
        working_directory = self.working_directory
        self.olive_dir = os.path.join(working_directory, "ank_olive")
# Update these based on working directory
        self.vde_socket_name  = os.path.join(self.olive_dir, "ank_vde_olive")
        self.vde_mgmt_socket_name  = os.path.join(self.olive_dir, "ank_vde_olive_mgmt")
        self.snapshot_folder = os.path.join(self.olive_dir, "snapshots")
# need to create this folder if not present
        self.socket_folder = os.path.join(self.olive_dir, "sockets")
        required_folders = [self.olive_dir, self.snapshot_folder, self.socket_folder]
        for folder in required_folders:
            chk_cmd = "stat -t %s" % folder
            result = self.get_command_output(chk_cmd)
            if "stat: cannot stat" in result:
                LOG.debug( "Creating folder %s" % folder)
                shell.sendline("mkdir %s" % folder)
                shell.prompt() 
            else:
                LOG.debug( "%s exists" % folder)
        ""
    def telnet_and_override(self, telnet_port, wait_for_bootup=False):
        shell = self.shell
        shell.sendline("telnet localhost %s" % telnet_port)

        """TODO: capture these:
        Booting [/kernel]...               
        ***** FILE SYSTEM MARKED CLEAN *****
        Creating initial configuration...
        """
        if wait_for_bootup:
            ready_prompt = "starting local daemons"
        else:
            ready_prompt = "Escape character is"

        for loop_count in range(0, 100):
            i = shell.expect([pexpect.TIMEOUT, ready_prompt, 
                "Consoles: serial port",
                "Booting \[/kernel\]\.",
                "Initializing M/T platform properties",
                "Trying to mount root",
                "Creating initial configuration",
                "Automatic reboot in progress...",
                "Doing initial network setup",
                "Doing additional network setup",
                ]) 
            if i == 0:
# Matched, continue on
                pass
            elif i == 1:
                LOG.info( "Logging into Olive")
                break
            else:
                # print the progress status message
                LOG.info("Startup progress: %s", shell.match.group(0))

# timedout, wait
        shell.expect("login:")
        shell.sendline("root")
        shell.expect("Password:")
        shell.sendline("Clouds")
        shell.expect("root@base-image%")
# Now load our ank config
        LOG.info( "Commiting configuration")
        shell.sendline("/usr/sbin/cli -c 'configure; load override ANK.conf; commit'")
        shell.expect("commit complete")
# logout, expect a new login prompt
        shell.sendline("exit")
        shell.expect("login:")
# Now disconnect telnet
        shell.sendcontrol("]")
        shell.expect("telnet>")
        shell.sendcontrol("D")
        shell.expect("Connection closed")
        LOG.info( "Configuration committed to Olive")
        shell.prompt()
        return

    def start_olives(self):
        """ Starts Olives inside Qemu
        Steps:
        1. Create bash script to start the Olives
        2. Copy bash script to remote host
        3. Start bash script as sudo
        """
        shell = self.shell
        LOG.info( "Starting Olives")

# transfer over junos lab

        tar_file = os.path.join(config.ank_main_dir, self.network.compiled_labs['junos'])
        self.transfer_file(tar_file, self.olive_dir)
        junos_extract_directory = os.path.join(self.olive_dir, "configset")
        
# Tar file copied across (if remote host) to local directory
        shell.sendline("cd %s" % self.olive_dir) 
# Remove any previous lab
        shell.sendline("rm -rf  " + junos_extract_directory)
        shell.prompt() 
        shell.sendline("mkdir  " + junos_extract_directory )
        shell.prompt() 

        tar_basename = os.path.basename(tar_file)
        
        # Need to force directory to extract to (junosphere format for tar extracts to cwd)
        LOG.debug( "Extracting Olive configurations")
        shell.sendline("tar -xzf %s -C %s" % (tar_basename, junos_extract_directory))
#Need this tar check or all else breaks!
        shell.expect("tar: Removing leading")
        shell.prompt() 

        configset_directory = os.path.join(junos_extract_directory, "configset")
        working_directory = self.get_cwd()
        configset_directory_full_path = os.path.join(working_directory, configset_directory)
# TODO: store these from junos compiler in network.compiled_labs dict
        config_files = {}
        for node in self.network.graph.nodes():
            node_filename = ank.rtr_folder_name(self.network, node)
            config_files[node] = {}
            config_files[node]['name'] = node_filename
            config_files[node]['config_file_full_path'] = (os.path.join(working_directory, configset_directory,
                "%s.conf" % node_filename))
            config_files[node]['config_file_snapshot'] = os.path.join(self.snapshot_folder, "%s.iso" % node_filename)
            config_files[node]['base_image_snapshot'] = os.path.join(self.snapshot_folder, "%s.img" % node_filename)
            config_files[node]['monitor_socket'] = os.path.join(configset_directory_full_path, "%s-monitor.sock" % node_filename)

        LOG.debug("Making ISO FS")
        for node, data in config_files.items():
            cmd = "mkisofs -o %s %s " % (data.get('config_file_snapshot'), 
                    data.get('config_file_full_path'))
            shell.sendline(cmd)
            shell.expect(["extents written"])
        shell.prompt()

        LOG.info("Running qemu-img")
        for node, data in config_files.items():
            cmd =  "qemu-img create -f qcow2 -b %s %s" % (self.base_image,
                    data['base_image_snapshot'])
            shell.sendline(cmd)
            shell.expect(["Formatting"])
            shell.sendline(cmd)

        shell.prompt()
    
        unallocated_ports = self.unallocated_ports()
        qemu_routers = []

        LOG.debug("Starting qemu machines")

        router_info_tuple = namedtuple('router_info', 'router_name, iso_image, img_image, mac_addresses, telnet_port, switch_socket, monitor_socket')
        
        for router_id, router in enumerate(self.network.graph):
            mac_list = self.mac_address_list(router_id, 6)
            router_info = router_info_tuple(
                    config_files[router].get('name'),
                    config_files[router].get('config_file_snapshot'),
                    config_files[router].get('base_image_snapshot'),
# create 6 mac addresses, the maximum per Olive
                    mac_list,
                    unallocated_ports.next(),
                    self.vde_socket_name,
                    config_files[router].get('monitor_socket'),
                    )
            qemu_routers.append(router_info)

        startup_template = lookup.get_template("autonetkit/olive_startup.mako")

    
#TODO: Sort routers by name so start in a more sensible order
        qemu_routers = sorted(qemu_routers, key=lambda router: router.router_name)
        for router in qemu_routers:
            LOG.info( "Starting %s" % router.router_name)
            startup_command = startup_template.render(
                    router_info = router
                    )

# flatten into single line
            startup_command = " ".join(item for item in startup_command.split("\n"))
            shell.sendline(startup_command)
# Telnet in
            shell.prompt()
            self.telnet_and_override(router.telnet_port, wait_for_bootup=True)

        LOG.info( "Successfully started all Olives")
        
    def start_switch(self):
        shell = self.shell

        LOG.info("Please enter sudo password and type '^]' (Control and right square bracket)"
                "to return to AutoNetkit")
        self.tap_name = "%s_%s" % (self.tap_name_base, self.linux_username)
        shell.sendline('sudo tunctl -u %s -t %s' % (self.linux_username, self.tap_name))
	sys.stdout.write (shell.after)
	sys.stdout.flush()
        shell.interact()
        LOG.info( "Starting vde_switch")
# Sendline in case user didn't have to sudo, and so didn't do anything
        shell.sendline()

# start vde switch
        start_vde_switch_cmd = "vde_switch -d -t %s -n 2000 -s %s -M %s" % (self.tap_name, 
                self.vde_socket_name, self.vde_mgmt_socket_name)
        LOG.info( "start command %s " % start_vde_switch_cmd)
        shell.sendline('%s' % start_vde_switch_cmd)
        i = shell.expect ([ "Address already in use" , "TUNSETIFF: Device or resource busy", pexpect.EOF])
        if i == 0:
            LOG.info( "vde_switch already running")
        elif i == 1:
            LOG.info( "Device busy, unable to create switch")
        else:
# started ok
            pass
        shell.prompt()

        return

    def deploy(self):
        if not self.connect_to_server():
# Problem starting ssh
            return
        self.check_required_programs()
        self.create_folders()
        self.start_switch()
        self.start_olives()

