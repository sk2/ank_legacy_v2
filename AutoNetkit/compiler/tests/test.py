import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import difflib

def test_netkit():
    master_dir = (resource_filename(__name__, "netkit"))
    inet = AutoNetkit.internet.Internet("multias", netkit=True) 
    inet.compile()

    f_lab = os.path.join(config.ank_main_dir, "netkit_lab", "lab.conf")
    test_lab_conf = open(f_lab, "r").read()
    master_lab_conf = open(os.path.join(master_dir, "lab.conf"), "r").read()
    try:
        assert(test_lab_conf == master_lab_conf)
    except AssertionError:
         message = ''.join(difflib.ndiff(test_lab_conf.splitlines(True),
                                                master_lab_conf.splitlines(True)))
         print message
         print "AAA"

    raise
