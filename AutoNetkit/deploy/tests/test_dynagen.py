import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")
import difflib

def test_dynagen_deploy():

config = """
    [Dynagen]
#image = /space/c7200-is-mz.124-19.image
image = /Users/sk2/Documents/c7200-is-mz.124-19.image
#working dir = /home/autonetkit/
working dir = /Users/sk2/ank/demo/ank_lab/
model = 7200
interfaces = "FastEthernet0/0", "FastEthernet0/1", "FastEthernet1/0", "FastEthernet1/1", "FastEthernet2/0", "FastEthernet2/1"
 #interfaces = "Ethernet0/0", "Ethernet0/1", "Ethernet1/0", "Ethernet1/1", "Ethernet2/0", "Ethernet2/1", "Ethernet3/0", "Ethernet3/1", "Ethernet4/0", "Ethernet4/1", "Ethernet5/0", "Ethernet5/1", "Ethernet6/0", "Ethernet6/1"
  [[Slots]]
  slot1 = PA-2FE-TX
  slot2 = PA-2FE-TX
  [[Options]]
  idlepc = 0x6085af60
  ram = 128
  [[Hypervisor]]
  server = 127.0.0.1
  port = 7202

[Dynagen Hosts]
  [[Mac]]
  host = localhost
  username = sk2
  active = 1
  collect data = 1
  dynagen binary = /Applications/Dynagen/Dynagen.app/Contents/MacOS/Dynagen
  """

    config.settings['Netkit Hosts'] = {
            'trc1': {
                "host": "trc1",
                "username": "autonetkit",
                "active": True,
                'collect data': True,
                'collect data commands': ['zebra: show ip route', 'ssh: uname -a'],
                }
            }
    inet = AutoNetkit.internet.Internet("2routers", netkit=True, deploy=True) 
    inet.compile()
    inet.deploy()
    inet.collect_data()

test_dynagen_deploy()
