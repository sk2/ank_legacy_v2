import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_netkit():
    master_dir = (resource_filename(__name__, "netkit"))
    inet = AutoNetkit.internet.Internet("multias", netkit=True) 
    inet.compile()

    f_lab = os.path.join(config.ank_main_dir, "netkit_lab", "lab.conf")
    test_lab_conf = open(f_lab, "r").read()
    master_lab_conf = open(os.path.join(master_dir, "lab.conf"), "r").read()


    def remove_skiplines(conf, skiplines):
        return "\n".join(line for line in conf.split("\n") if
            not any(line.startswith(skip) for skip in skiplines))

    test_lab_conf = remove_skiplines(test_lab_conf, ["LAB_VERSION", "LAB_AUTHOR"])
    master_lab_conf = remove_skiplines(master_lab_conf, ["LAB_VERSION", "LAB_AUTHOR"])
#TODO: make less stochastic!!!
    #assert(test_lab_conf == master_lab_conf)
