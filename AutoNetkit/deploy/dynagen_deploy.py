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
import re
import datetime
import pxssh
import sys
import AutoNetkit as ank
import itertools
import pprint
import netaddr
import threading

import Queue

# Used for EOF and TIMEOUT variables
import pexpect

LINUX_PROMPT = "~#"   

#TODO: tidy up folder handling esp wrt config.lab_dir config.junos_dir etc

from mako.lookup import TemplateLookup
from pkg_resources import resource_filename

template_cache_dir = config.template_cache_dir

template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )

class DynagenDeploy():  
    """ Deploy a given Junos lab to an Olive Host"""

    def __init__(self, host=None, username=None, network=None,
            host_alias = None,
            lab_dir="junos_config_dir"):
        self.server = None    
        self.lab_dir = lab_dir
        self.network = network 
        self.host_alias = host_alias
        self.host = host
        self.username = username
        self.shell = None
# For use on local machine
        self.shell_type = "bash"
        self.logfile = open( os.path.join(config.log_dir, "pxssh.log"), 'w')
        self.tap_name_base = "ank_tap_olive"
        self.host_data_dir = None
        self.dynagen_dir = config.ank_main_dir
        

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

    def get_shell(self):
        """Connects to Netkit server (if remote)"""   
        # Connects to the Linux machine running the Netkit lab   
        shell = None     
        if self.host and self.username:  
            # Connect to remote machine

#Note the code that checks if link alredy exists and returns it ruins setting up threads (as all use same)
#TODO: remove the shell_link bit from netkit deploy and make it use a self.shell variable instead

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
                LOG.warn("Specified Olive host is running Mac OS X, "
                    "please specify a Linux Olive host.")
                return None 
            else:
                LOG.warn("Provided Netkit host is not running Linux")

        return shell

    def connect_to_server(self):  
# Wrapper to work with existing code
        self.shell = self.get_shell()
        self.working_directory = self.get_cwd()
        self.linux_username = self.get_whoami()
        return True
    
    def transfer_file(self, local_file, remote_folder=""):
        """Transfers file to remote host using SCP"""
        # Sanity check
        if self.local_server:
            LOG.warn("Can only SCP to remote Netkit server")
            return

        scp_command = "scp %s %s@%s:%s" % (local_file,
            self.username, self.host, remote_folder)
        LOG.debug(scp_command)
        child = pexpect.spawn(scp_command)      
        child.logfile = self.logfile

        child.expect(pexpect.EOF) 
        LOG.debug(  "SCP result %s"% child.before.strip())
        return 

    def run_collect_data_command(self, nodes_with_port, commands, shell):
            node, router_name, telnet_port = nodes_with_port
# Unique as includes ASN etc
#TODO: check difference, if really need this...
            full_routername = node.rtr_folder_name 

# use format as % gets mixed up
            LOG.info("Logging into %s" % router_name)
            router_name_junos = router_name
#workaround for gh-120
            if "." in router_name:
                router_name_junos = router_name.split(".")[0]
            root_prompt = "root@{0}%".format(router_name_junos)
            shell.sendline("telnet localhost %s" % telnet_port)
            shell.expect("Escape character is ")
            shell.sendline()

            i = shell.expect(["login", root_prompt]) 
            if i == 0:
# Need to login
                shell.sendline("root")
                shell.expect("Password:")
                shell.sendline("Clouds")
                shell.expect(root_prompt)
            elif i == 1:
# logged in already
                pass

# Now load our ank config
            for command in commands:
                command_to_send = "echo %s |cli" % command
                LOG.info("%s: running command %s" % (router_name, command))
                shell.sendline(command_to_send)
                shell.expect(root_prompt)
                command_output = shell.before
# from http://stackoverflow.com/q/295135/
                command_filename_format = (re.sub('[^\w\s-]', '', command).strip().lower())
                filename = "%s_%s_%s.txt" % (full_routername,
                        command_filename_format,
                        time.strftime("%Y%m%d_%H%M%S", time.localtime()))
                filename = os.path.join(self.host_data_dir, filename)
                
                with open( filename, 'w') as f_out:
                    f_out.write(command_output)

# logout, expect a new login prompt
            shell.sendline("exit")
            shell.expect("login:")
# Now disconnect telnet
            shell.sendcontrol("]")
            shell.expect("telnet>")
            shell.sendcontrol("D")
            shell.expect("Connection closed")
            shell.prompt()
            return

    def collect_data(self, commands):
        """Runs specified collect_data commands"""
        LOG.info("Collecting data for %s" % self.host_alias)
        LOG.warn("Data collection not yet implemented for Dynagen")

    def deploy(self):
        if not self.connect_to_server():
            LOG.warn("Unable to start shell for %s" % self.host_alias)
# Problem starting ssh
            return
        shell = self.shell
        LOG.info( "Starting Dynagen")

# transfer over junos lab

        tar_file = os.path.join(config.ank_main_dir, self.network.compiled_labs['dynagen'])
        self.transfer_file(tar_file)
#TODO: make just the "junos_dir" accessible from the config directly (without the ank_lab part)
        dynagen_lab_dir = os.path.join(self.dynagen_dir, "dynagen_lab")
        configset_directory = os.path.join(dynagen_lab_dir, "configset")
        
# Tar file copied across (if remote host) to local directory
        #shell.sendline("cd %s" % self.olive_dir) 
        shell.sendline("cd")
# Remove any previous lab
        shell.sendline("rm -rf  " + configset_directory)
        shell.prompt() 

        tar_basename = os.path.basename(tar_file)
        
        # Need to force directory to extract to (junosphere format for tar extracts to cwd)
        LOG.debug( "Extracting Dynagen configurations")
        shell.sendline("tar -xzf %s" % (tar_basename))
#Need this tar check or all else breaks!
        shell.prompt() 

        # Now move into lab directory to create images
        shell.sendline("cd %s" % dynagen_lab_dir) 
        shell.prompt()
#TODO: parameterise lab.net
        LOG.info("Starting Dynagen lab")
        shell.sendline("dynagen lab.net")
#TODO: capture bootup process similar to for Olives
        ready_prompt = "=>"

        started_successfully = False

#TODO: explain why 100 used here
        for loop_count in range(0, 100):
            i = shell.expect([
                pexpect.TIMEOUT,
                ready_prompt,
                "Press ENTER to continue",
                "\*\*\* Warning:\s*(\w*\s*)*",
                "\*\*\* Error:\s*(\w*\s*)*",
                ]) 
            if i == 0:
# Matched, continue on
                LOG.info("Timeout starting Dynagen lab")
                break
            elif i == 1:
                LOG.info( "Dynagen: started lab")
                started_successfully = True
                break
            elif i == 2:
                LOG.info("Unable to start Dynagen lab")
                break
            elif i == 3:
                # TODO: fix this split after "Warning:" --- as too complex to regex capture
                error_message = shell.match.group(0).split("Warning:")[1].strip()
                LOG.info("Problem starting Dynagen lab: %s" % error_message)
            elif i == 4:
                error_message = shell.match.group(0).split("Error:")[1].strip()
                LOG.info("Problem starting Dynagen lab: %s" % error_message)
            else:
                # print the progress status me= ssage
                progress_message = shell.match.group(0)
                LOG.info("Startup progress: %s" % (progress_message))

        if started_successfully:
            LOG.info("Interacting with Dynagen lab, press '^]' (Control and right square bracket) "
                    "to return to AutoNetkit")
            sys.stdout.write (shell.after)
            sys.stdout.flush()
            shell.interact()


#Now launch lab



