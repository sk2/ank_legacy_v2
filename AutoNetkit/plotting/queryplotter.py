import AutoNetkit as ank
import networkx as nx

class QueryPlotter(object):
    def __init__(self, network):
        self.network = network
        self.pos = nx.spring_layout(network.graph)

    def plot(self, nodes):
# colors for highlighted nodes
        colors = [] 
        for n in self.network.graph:
            if n in nodes:
                colors.append('r')
            else:
                colors.append('b')
        ank.plot_graph(self.network.graph, pos=self.pos, node_color=colors, show=True)

