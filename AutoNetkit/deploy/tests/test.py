import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_netkit_deploy():
    #TODO: get nosetests to use ssh key to log into deployment machine.... or simulate using pexpect filehandles
    return
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

   
