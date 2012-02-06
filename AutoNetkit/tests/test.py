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

    f_test = os.path.join(config.log_dir, "bgp.txt")
    test_file = open(f_test, "r").read()
    master_file = open(os.path.join(master_dir, "bgp.txt"), "r").read()

    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

    f_test = os.path.join(config.log_dir, "physical.txt")
    test_file = open(f_test, "r").read()
    master_file = open(os.path.join(master_dir, "physical.txt"), "r").read()

    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError


