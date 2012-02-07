import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def remove_skiplines(conf, skiplines):
    return "\n".join(line for line in conf.split("\n") if
            not any(line.lstrip().startswith(skip) for skip in skiplines))

def test_netkit():
    master_dir = (resource_filename(__name__, "netkit"))
    inet = AutoNetkit.internet.Internet("multias", netkit=True) 
    inet.compile()

    f_lab = os.path.join(config.ank_main_dir, "netkit_lab", "lab.conf")
    test_file = open(f_lab, "Ur").read()
    master_file = open(os.path.join(master_dir, "lab.conf"), "Ur").read()
    skiplines = ["LAB_VERSION", "LAB_AUTHOR"] 
    test_file = remove_skiplines(test_file, skiplines)
    master_file = remove_skiplines(master_file, skiplines)
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

    f_test = os.path.join(config.ank_main_dir, "netkit_lab", "shared.startup")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "shared.startup"), "Ur").read()
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

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

def test_junosphere():
    master_dir = (resource_filename(__name__, "junosphere_vjx"))
    inet = AutoNetkit.internet.Internet("multias", junosphere=True) 
    inet.compile()

    f_test = os.path.join(config.ank_main_dir, "junos_lab", "topology.vmm")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "topology.vmm"), "Ur").read()
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

    f_test = os.path.join(config.junos_dir, "configset", "1c_AS1.conf")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "1c_AS1.conf"), "Ur").read()
    skiplines = ["message"] 
    test_file = remove_skiplines(test_file, skiplines)
    master_file = remove_skiplines(master_file, skiplines)
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

def test_junosphere_olive():
    config.settings['Junosphere']['platform'] = "Olive"
    
    master_dir = (resource_filename(__name__, "junosphere_olive"))
    inet = AutoNetkit.internet.Internet("multias", junosphere=True) 
    inet.compile()

    f_test = os.path.join(config.ank_main_dir, "junos_lab", "topology.vmm")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "topology.vmm"), "Ur").read()
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

    f_test = os.path.join(config.junos_dir, "configset", "1c_AS1.conf")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "1c_AS1.conf"), "Ur").read()
    skiplines = ["message"] 
    test_file = remove_skiplines(test_file, skiplines)
    master_file = remove_skiplines(master_file, skiplines)
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError


def test_dynagen():
    config.settings['Dynagen'] = {
            "image": "/space/c7200-is-mz.124-19.image",
            "working dir": "/home/autonetkit/",
            "model": 7200,
            "interfaces": ["Ethernet0/0", "Ethernet0/1", "Ethernet1/0", "Ethernet1/1", "Ethernet2/0", "Ethernet2/1", "Ethernet3/0", "Ethernet3/1", "Ethernet4/0", "Ethernet4/1", "Ethernet5/0", "Ethernet5/1", "Ethernet6/0", "Ethernet6/1"],
            "Slots": { "slot1": "PA-2FE-TX", "slot2": "PA-2FE-TX"},
            "Options": { "idlepc": "0x6085af60", "ram": 128},
            "Hypervisor": {"server": "127.0.0.1", "port": 7202},
            }
    master_dir = (resource_filename(__name__, "dynagen"))
    inet = AutoNetkit.internet.Internet("multias", dynagen=True) 
    inet.compile()

    f_test = os.path.join(config.dynagen_dir, "lab.net")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "lab.net"), "Ur").read()
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

    f_test = os.path.join(config.dynagen_dir, "configs", "1c_AS1.conf")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "1c_AS1.conf"), "Ur").read()
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError

def test_olive():
    master_dir = (resource_filename(__name__, "olive"))
    inet = AutoNetkit.internet.Internet("multias", olive=True) 
    inet.compile()

    f_test = os.path.join(config.junos_dir, "configset", "1c_AS1.conf")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "1c_AS1.conf"), "Ur").read()
    skiplines = ["message"] 
    test_file = remove_skiplines(test_file, skiplines)
    master_file = remove_skiplines(master_file, skiplines)
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError


def test_cbgp():
    master_dir = (resource_filename(__name__, "cbgp"))
    inet = AutoNetkit.internet.Internet("multias", cbgp=True) 
    inet.compile()

    f_test = os.path.join(config.cbgp_dir, "cbgp.cli")
    test_file = open(f_test, "Ur").read()
    master_file = open(os.path.join(master_dir, "cbgp.cli"), "Ur").read()
    try:
        assert(test_file == master_file)
    except AssertionError:
        message = ''.join(difflib.ndiff(test_file.splitlines(True),
            master_file.splitlines(True)))
        LOG.warn(message)
        raise AssertionError
