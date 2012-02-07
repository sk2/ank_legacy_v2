# -*- coding: utf-8 -*-
"""
Deploy a given Olive lab to an Olive server
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

import logging
LOG = logging.getLogger("ANK")
                                 
from collections import namedtuple
                                 
import os
import time
import AutoNetkit.config as config
import re
import datetime
import sys
import AutoNetkit as ank
import itertools
import pprint
import netaddr
import threading

import Queue

# Used for EOF and TIMEOUT variables
try:
    import pexpect
    import pxssh
except ImportError:
    LOG.error("Netkit deployment requires pexpect")

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

class cBGPDeploy():  
    """ Deploy a given cBGP lab to the local Host"""

    def __init__(self, network=None):
        self.server = None    
        self.network = network 
        self.shell = None
        self.shell_type = "bash"
# For use on local machine
        self.logfile = open( os.path.join(config.log_dir, "pxssh.log"), 'w')
        self.host_data_dir = None
        self.cbgp_dir = config.cbgp_dir
        
    def get_shell(self):
        """Connects to Local server"""   
        # Connects to the Local machine running the Netkit lab   
        shell = pexpect.spawn (self.shell_type) 
        shell.logfile = self.logfile
        shell.setecho(False)  
        return shell

    def collect_data(self):
        LOG.warn("Data collection not yet implemented for cBGP")

    def deploy(self):
        shell = self.get_shell()
#TODO: make cbgp.cli a parameter/variable
#TODO: fix multiline error messages - or specify in lab the file to save cbgp logs to
        cbgp_file = os.path.join(self.cbgp_dir, "cbgp.cli")
        shell.sendline("cbgp -c %s; echo done" % cbgp_file)
        for loop_count in range(0, 100):
            i = shell.expect([pexpect.EOF, "done", "Error:(.+)"])
            if i == 0:
                #TODO: see why not matching here
                print "DONE"
                break
            elif i == 1:
                break
            elif i == 2:
                LOG.info("cBGP error: %s" % shell.match.group(1).strip())
                pass






