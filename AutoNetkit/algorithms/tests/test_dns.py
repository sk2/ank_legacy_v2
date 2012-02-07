import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib


def test_dns():
    try:
        config.settings['DNS']['hierarchical'] = True
        master_dir = (resource_filename(__name__, "dns"))
        inet = AutoNetkit.internet.Internet("multias", netkit=True) 
        inet.compile()
    finally:
        config.settings['DNS']['hierarchical'] = False

    root_files = ["db.root", "named.conf"]
    for root_file in root_files:
        f_test = os.path.join(config.lab_dir, "rootdns1_AS2", "etc", "bind", root_file)
        test_file = open(f_test, "Ur").read()
        master_file = open(os.path.join(master_dir, "rootdns1_AS2", "etc", "bind", root_file), "Ur").read()
        try:
            assert(test_file == master_file)
        except AssertionError:
            message = ''.join(difflib.ndiff(test_file.splitlines(True),
                master_file.splitlines(True)))
            LOG.warn(message)
            raise AssertionError

    l3_files = ["db.0.10.in-addr.arpa", "db.AS1", "db.root", "named.conf"]
    for l3_file in l3_files:
        f_test = os.path.join(config.lab_dir, "l31dns1_AS1", "etc", "bind", l3_file)
        test_file = open(f_test, "Ur").read()
        master_file = open(os.path.join(master_dir, "l31dns1_AS1", "etc", "bind", l3_file), "Ur").read()
        try:
            assert(test_file == master_file)
        except AssertionError:
            message = ''.join(difflib.ndiff(test_file.splitlines(True),
                master_file.splitlines(True)))
            LOG.warn(message)
            raise AssertionError

