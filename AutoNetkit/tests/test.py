import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_dumps():
    master_dir = (resource_filename(__name__, "comparisons"))
    inet = AutoNetkit.internet.Internet("multias", netkit=True) 
    inet.compile()
    inet.dump()

    f_bgp = os.path.join(config.log_dir, "bgp.txt")
    test_bgp = open(f_bgp, "r").read()
    master_bgp = open(os.path.join(master_dir, "bgp.txt"), "r").read()

    assert(test_bgp == master_bgp)

    f_phys = os.path.join(config.log_dir, "physical.txt")
    test_phys = open(f_phys, "r").read()
    master_phys = open(os.path.join(master_dir, "physical.txt"), "r").read()

    try:
        assert(test_phys == master_phys)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_phys.splitlines(True),
            master_phys.splitlines(True)))
        LOG.warn(message)
        raise AssertionError
