import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_graph_product():
    master_dir = (resource_filename(__name__, "comparisons"))
    gp_in_file = resource_filename("AutoNetkit","lib/examples/topologies/gptest.graphml")
    LOG.warn(gp_in_file)
    inet = AutoNetkit.internet.Internet(gp_in_file) 
    inet.compile()
    inet.dump()

    f_bgp = os.path.join(config.log_dir, "physical.txt")
    test_file = open(f_bgp, "r").read()
    master_file = open(os.path.join(master_dir, "graph_prod_physical.txt"), "r").read()

    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError
