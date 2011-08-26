class Input(object):
    """Plugins of this class create an AutoNetkit object"""

    def run(self):
        """Takes nothing, returns network"""
        return network
        
class Update(object):
    """Plugins of this class update an AutoNetkit network"""

    def run(self, network):
        """Takes network, returns network"""
        return network
        
class Output(object):
    """Plugins of this class output from an autonetkit network"""

    def run(self, network):
        """Takes network, returns nothing"""
        return                         
        
                      
class Netkit(object):
    """Plugins of this class interact with a Netkit server"""

    pass