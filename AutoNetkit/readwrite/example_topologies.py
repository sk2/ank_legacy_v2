# -*- coding: utf-8 -*-
"""
Example Topologies
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen

__all__ = ['load_example']
import os
from pkg_resources import resource_filename
import AutoNetkit as ank


import glob

import logging
LOG = logging.getLogger("ANK")


def load_example(filename):
    """
    Load example network
    """
    # No extension, see if filename is an included example Topology
    topology_dir =  resource_filename("AutoNetkit",
                os.path.join("lib", "examples", "topologies"))
    test_filename = os.path.join(topology_dir, "%s.graphml" % filename)
    if os.path.isfile(test_filename):
            LOG.info("Loading example topology %s " % filename)
            return ank.load_graphml(test_filename)
    else:
            example_files = glob.glob(topology_dir + os.sep + "*.graphml")
# Remove path
            example_files = (os.path.split(filename)[1] for filename in example_files)
# Remove extension
            example_files = (os.path.splitext(filename)[0] for filename in example_files)
            LOG.warn("Unable to find example topology %s" % filename)
            LOG.info("Valid example topologies are: " + ", ".join(example_files))
            

