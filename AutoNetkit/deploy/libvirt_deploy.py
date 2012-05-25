# -*- coding: utf-8 -*-
"""
Deploy a given Libvirt lab to an Libvirt server
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

import logging
LOG = logging.getLogger("ANK")
                                 
import os
import AutoNetkit.config as config

import AutoNetkit as ank

from mako.lookup import TemplateLookup
from mako.template import Template
from pkg_resources import resource_filename
mako_tmp_dir = '/tmp/mako_modules'

template_cache_dir = config.template_cache_dir

template_dir =  resource_filename("AutoNetkit","lib/templates")
lookup = TemplateLookup(directories=[ template_dir ],
        module_directory= template_cache_dir,
        #cache_type='memory',
        #cache_enabled=True,
        )

class LibvirtDeploy():  
    """ Deploy a given Junos lab to an Olive Host"""

    def __init__(self, host=None, username=None, network=None, script_data=None):
        self.server = None    
        self.network = network 
        self.host = host
        self.username = username
        self.script_data = script_data

    def transfer(self):
        """Transfers file to remote host using script"""
        LOG.info("Transferring libvirt to remote host")
        template_file = os.path.join(self.script_data['base dir'], self.script_data['Transfer']['location'])
        mytemplate = Template(filename=template_file, module_directory= mako_tmp_dir)
        tar_file = os.path.join(config.libvirt_dir, self.network.compiled_labs['libvirt'][self.host])
        command =  mytemplate.render(
                tar_file = tar_file,
                **self.script_data['Transfer']) # pass in user defined variables
        #result = os.system(command)

        template_file = os.path.join(self.script_data['base dir'], self.script_data['Shell']['location'])
        mytemplate = Template(filename=template_file, module_directory= mako_tmp_dir)
        tar_file = os.path.join(config.libvirt_dir, self.network.compiled_labs['libvirt'][self.host])
        shell =  mytemplate.render(
                **self.script_data['Shell']) # pass in user defined variables
        shell = shell.strip()
        untarred_directory = os.path.join(config.libvirt_dir, self.host) 
        dst_file, _ = os.path.splitext(self.script_data['Create']['location'])
        dst_file = os.path.join(untarred_directory, dst_file)
        run_command = "%s sh -x %s" % (shell, dst_file)
        print run_command
        result = os.system(run_command)

