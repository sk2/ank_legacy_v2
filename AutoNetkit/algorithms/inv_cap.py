# -*- coding: utf-8 -*-
"""
Inverse capacity link weight functions
"""

import AutoNetkit as ank

def inv_cap_weights(network):
    """Updates link weights based on inverse of link speed."""
    #TODO: rewrite this to be cleaner iteration and setting
    for graph in ank.get_as_graphs(network):
        for (src, dst, data) in graph.edges_iter(data=True):    
            # only update if non default weight       
            if 'speed' in data and 'weight' in data and data['weight'] == 1: 
                # assume largest link is 10gb 
                #TODO: use Cisco guidelines for this
                scale_speed = 100000      
                speed = float(data['speed'])
                weight = int((1/speed)*scale_speed)    
                weight = max(weight, 1)
                if weight is 0:
                    weight = 1
                    graph[src][dst]['weight'] = weight
                    network.set_edge_property(src, dst, 'weight', weight)
    return
