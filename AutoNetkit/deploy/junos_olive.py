# -*- coding: utf-8 -*-
"""
Deploy a given Netkit lab to a Netkit server
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen, Askar Jaboldinov 

import logging
LOG = logging.getLogger("ANK")
                                 
import os
import time
import AutoNetkit.config as config
import pxssh

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

    def __init__(self, host=None, username=None):
        self.server = None    
        self.lab_dir = None
        self.network = None
        self.host = host
        self.username = username
        self.shell = None
        self.shell_type ="bash"
        self.logfile = open( os.path.join(config.log_dir, "pxssh.log"), 'w')
        
        

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
            #TODO: set state to Netkit
        else:   
            shell = pexpect.spawn (self.shell_type) 
            shell.sendline("uname")
            
            shell.logfile = self.logfile    
            shell.setecho(True)  
            # Check Linux machine (Netkit won't run on other Unixes)   
            i = shell.expect(["Linux", "Darwin", pexpect.EOF, LINUX_PROMPT]) 
            if i == 0:
                # Machine is running Linux. Send test command (ignore result)
                shell.sendline("ls") 
            elif i == 1:
                LOG.warn("Specified Netkit host is running Mac OS X, "
                    "please specify a Linux Netkit host.")
                return None 
            else:
                LOG.warn("Provided Netkit host is not running Linux")

        self.shell = shell   
        return

    def create_bash_script(self):
        bash_template = lookup.get_template("autonetkit/olive_startup.mako")
        

    def start_switch(self):
        shell = self.shell
        chk_cmd = 'hash vde_switch 2>&- && echo "Present" || echo >&2 "Absent"\n'
        shell.sendline(chk_cmd)
        vde_switch_installed = shell.expect (["Absent", "Present"])    
        if vde_switch_installed:
            print "vde switch installed"
        else:
            #TODO: convert print to LOGs
            print "vde switch not installed"
            return False
        shell.prompt() 
        chk_cmd = 'hash tunctl 2>&- && echo "Present" || echo >&2 "Absent"\n'
        shell.sendline(chk_cmd)
        tunctl_switch_installed = shell.expect (["Absent", "Present"])    
        if tunctl_switch_installed:
            print "tunctl installed"
        else:
            print "tunctl not installed"
            return False
        shell.prompt() 
        tapname = "ank_tap_olive"
        print "Please enter sudo password and type 'exit' to return to AutoNetkit"
        shell.sendline('sudo tunctl -t %s' % tapname)
        shell.interact()
        return

# check if tunnel active

        chk_cmd = "ifconfig ank_tap_olive"
        shell.sendline(chk_cmd)

        shell.sendline('tunctl -t %s' % tapname)
        shell.prompt() 
        result = shell.before 
        result = shell.after
        print "result from starting is ", result






olive_deploy = OliveDeploy(host="trc1", username="sknight")
olive_deploy.connect_to_server()
olive_deploy.start_switch()
olive_deploy.create_bash_script()

