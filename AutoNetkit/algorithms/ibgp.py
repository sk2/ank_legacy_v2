import networkx as nx
import pprint
import itertools

#TODO: can remove this

G_physical = nx.read_graphml("ibgp_example.graphml")
pprint.pprint(G_physical.nodes(data=True))

G_session = nx.DiGraph()
G_session.add_nodes_from(G_physical)

#TODO: add check that PoP is set for all nodes

#TODO: first look at nodes with cluster_id set

# All pairs
for (s,t) in ((s,t) for s in G_physical.nodes() for t in G_physical.nodes() if s!= t):
    s_level = int(G_physical.node[s].get("ibgp_level"))
    t_level = int(G_physical.node[t].get("ibgp_level"))
# Intra-PoP
#TODO: also make Intra-Cluster
    if (
            (G_physical.node[s].get("PoP") == G_physical.node[t].get("PoP")) # same PoP
            or (G_physical.node[s].get("ibgp_cluster") == G_physical.node[t].get("ibgp_cluster") != None) # same cluster and cluster is set
            ):
        if s_level == t_level == 1:
            # client to client: do nothing
            pass
        elif (s_level == 1) and (t_level == 2):
            # client -> server: up
            G_session.add_edge(s, t, sig_dir = 'u')
        elif (s_level == 2) and (t_level == 1):
            # server -> client: down
            G_session.add_edge(s, t, sig_dir = 'd')
        elif s_level == t_level == 2:
            # server -> server: over
            G_session.add_edge(s, t, sig_dir = 'o')
    else:
# Inter-PoP
        if s_level == t_level == 2:
            G_session.add_edge(s, t, sig_dir = 'o')

            # Add some properties for debugging/testing in yED
for n in G_session:
    G_session.node[n]['label'] = G_physical.node[n].get("label")
    G_session.node[n]['PoP'] = G_physical.node[n].get("PoP")

nx.write_graphml(G_session, "g_session.graphml")

try:
    import matplotlib.pyplot as plt

# Note: shells only works for 2 dimensions
    shells = [ [n for n in G_session if int(G_physical.node[n].get("ibgp_level")) ==2],
            [n for n in G_session if int(G_physical.node[n].get("ibgp_level")) ==1]]
    pos=nx.shell_layout(G_session, shells)

    labels = dict( (n, G_physical.node[n].get('label')) for n in G_session)
    nx.draw(G_session, pos, labels=labels, arrows=False, node_color = "0.8", edge_color="0.8")

# NetworkX will automatically put a box behind label, make invisible
# by setting alpha to zero
    bbox = dict(boxstyle='round',
            ec=(1.0, 1.0, 1.0, 0),
            fc=(1.0, 1.0, 1.0, 0.0),
            )      

    def sig_dir_to_arrow(sig_dir):
        """Nicer labels for plotting"""
        mapping = {'o': '', 'u': 'u', 'd': 'd'}
        return mapping[sig_dir]

    edge_labels = dict( ((s,t), sig_dir_to_arrow(d.get('sig_dir'))) for s,t,d in G_session.edges(data=True))
    nx.draw_networkx_edge_labels(G_session, pos, edge_labels, label_pos = 0.8, bbox = bbox)

    plt.show()
    plt.savefig("g_session.pdf")

except:
    print "Error loading matplotlib, plotting disabled"



