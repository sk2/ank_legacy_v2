import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib


def test_dns():
    return
    config.settings['DNS']['hierarchical'] = True
    master_dir = (resource_filename(__name__, "netkit"))
    inet = AutoNetkit.internet.Internet("multias", netkit=True) 
    inet.compile()

    return

    zebra_files = ["bgpd.conf", "daemons", "ospfd.conf", "zebra.conf"]
    for z_file in zebra_files:
        f_test = os.path.join(config.ank_main_dir, "netkit_lab", "1c_AS1", "etc", "zebra", z_file)
        test_file = open(f_test, "Ur").read()
        LOG.info(test_file)
        master_file = open(os.path.join(master_dir, "1c_as1_zebra", z_file), "Ur").read()
        try:
            assert(test_file == master_file)
        except AssertionError:
            message = ''.join(difflib.ndiff(test_file.splitlines(True),
                master_file.splitlines(True)))
            LOG.warn(message)
            LOG.warn(f_test)
            LOG.warn(os.path.join(master_dir, "1c_as1_zebra", z_file))
            raise AssertionError

