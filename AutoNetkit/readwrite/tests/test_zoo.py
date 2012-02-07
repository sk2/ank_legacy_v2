import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_zoo():
    return
    """
    master_dir = (resource_filename(__name__, ""))
    master_file = open(os.path.join(master_dir, "Aarnet.gml"), "Ur").read()
    LOG.warn(master_file)
    inet = AutoNetkit.internet.Internet(master_file) 
    inet.compile()
    inet.dump()
    nodes = []
    assert(inet.network.graph.nodes() == nodes)
    LOG.warn(inet.network.graph.nodes())
    assert(1==2)
    """
