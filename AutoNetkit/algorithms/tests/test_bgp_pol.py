import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")

def test_bgp_pol():
    master_dir = (resource_filename(__name__, "comparisons"))
    pol_file = os.path.join(master_dir, "policy.txt")
    inet = AutoNetkit.internet.Internet("multias", netkit=True, policy_file=pol_file) 
    inet.compile()
    inet.dump()

    f_bgp = os.path.join(config.log_dir, "bgp.txt")
    test_bgp = open(f_bgp, "r").read()
    master_bgp = open(os.path.join(master_dir, "bgp_dump.txt"), "r").read()

    assert(test_bgp == master_bgp)
