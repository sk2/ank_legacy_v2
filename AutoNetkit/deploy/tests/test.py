import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_netkit_deploy():
    config.settings['Netkit Hosts'] = {
            'trc1': {
                "host": "trc1",
                "username": "autonetkit",
                "active": True,
                }
            }
    inet = AutoNetkit.internet.Internet("2routers", netkit=True, deploy=True) 
    inet.compile()
    inet.deploy()
    assert(1==2)

   
