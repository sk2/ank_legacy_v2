import os
import AutoNetkit
import AutoNetkit.config as config
from pkg_resources import resource_filename
import logging
LOG = logging.getLogger("ANK")

def test_olive_deploy():
    return
    config.settings = config.reload_config()
    master_dir = (resource_filename(__name__, ""))
    config_file = os.path.join(master_dir, "olive.cfg")
    config.merge_config(config_file)
    print config.settings

    inet = AutoNetkit.internet.Internet("2routers", netkit=True, deploy=True) 
    inet.compile()
    inet.deploy()
    inet.collect_data()
    config.settings = config.reload_config()
#TODO: get feedback that machine started ok - need to store in the netkit server
