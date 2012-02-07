import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_bgp_pol():
    master_dir = (resource_filename(__name__, "comparisons"))
    pol_file = os.path.join(master_dir, "policy.txt")
    inet = AutoNetkit.internet.Internet("multias", netkit=True, policy_file=pol_file) 
    inet.compile()
    inet.dump()

    f_bgp = os.path.join(config.log_dir, "bgp.txt")
    test_file = open(f_bgp, "Ur").read()
    master_file = open(os.path.join(master_dir, "bgp_dump.txt"), "Ur").read()

    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError
