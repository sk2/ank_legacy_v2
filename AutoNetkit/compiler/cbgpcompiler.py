"""
Generate GNS3 configuration files for a network 
"""
import beaker
from mako.lookup import TemplateLookup    

from pkg_resources import resource_filename         

import os
import networkx as nx  
import logging
LOG = logging.getLogger("ANK")

import AutoNetkit as ank

class CbgpCompiler:  
    """Compiler main"""

    def __init__(self, network, services):
        self.network = network
        self.services = services

    def configure(self):  
        """Generates cBGP specific configuration files."""
        LOG.info("Configuring cBGP")

  
