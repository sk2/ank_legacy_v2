import networkx as nx
from nodes.router import Router    
import numpy as np   
import plot


"""
Useful references:

    http://mathworld.wolfram.com/GraphProduct.html
    http://en.wikipedia.org/wiki/Graph_operations
"""

def test(graph):
    (adj_a, labels_a) = nx.attr_matrix(graph)    
    
    H = nx.Graph()
    R1 = Router(1)
    R2 = Router(2)
    R3 = Router(3)
    #H.add_node(R1)
    H.add_edge(R1, R2)
    H.add_edge(R1, R3)
    (adj_b, labels_b) = nx.attr_matrix(H)

    #plot.show_graph(H, "H")
    #plot.show_graph(graph, "original")

    mat_a = np.matrix(adj_a)
    mat_b = np.matrix(adj_b)

    mat_new = cart(mat_a, mat_b)
    mat_new = strong(mat_a, mat_b)
    #TODO: fix rooted product
    #mat_new = rooted(mat_a, mat_b)

    labels = new_labels(labels_a, labels_b)     
    new_graph = mat_to_graph(mat_new, labels)
    #plot.show_graph(new_graph)

    return new_graph

def kron_prod(G, H):
    """
    Kronecker product

    :math:`adj(G \otimes H) = G \otimes H` """
    return np.kron(G,H)

def cart(G, H):
    """
    Cartesian product

    :math:`adj(G \square H) = G \oplus H` """
    return kron_sum(G,H)

def kron_sum(G, H):
    """
    Kronecker sum

    :math:`adj(G \oplus H) = G \oplus H` """
    m = np.size(G,1)
    n = np.size(H,1)
    return np.kron(G, np.eye(n)) + np.kron(H, np.eye(m))
    
def strong(G, H):
    """
    Strong product

    :math:`adj(G \\ast H) = G \oplus H + G \otimes H` """
    return kron_sum(G, H) + cart(G, H)

def rooted(G, b, k=1):
    """
    Rooted product

    :math:`adj(G \circ H) = G \otimes E_{m,k} + I_n \otimes H`

    k is location in b matrix that is used as root

    """
    n = np.size(G,1)
    m = max( np.size(b,1), np.size(H,2) )

    print "m {0} n {1}".format(m,n)
    #TODO: check value of k vs node labels - take in as parameter?
    return kron_prod(G, e_matrix(m,k)) +  kron_prod(np.eye(n), H)

def tensor(G, H):
    """
    Tensor product

    :math:`adj(G \\times H) = G \otimes H` """
    pass

def lexi(G, H):
    """
    Lexicographic product

    :math:`adj(G \cdot H) = G \otimes H` """
    pass

def e_matrix(m, k):
    """
    :math:`E_{m,k}` is a zero matrix of size m, with 1 at element (k,k)
    """
    e = np.zeros( (m,m) )
    e[k,k] = 1
    return e

    
def new_labels(G, H): 
    """ Generates labels for new matrix based on previous matrices
    
    eg [a, b, c] and [1, 2] will return [a_1, a_2, b_1, b_2, c_1, c_2]
    
    """
    #TODO: see if can do kronecker of arrays not matrices
    a = np.matrix(G)
    b = np.matrix(H)
    return np.kron(G, H)

def mat_to_graph(adj, labels):

    # Create directed graph to use
    new_graph = nx.from_numpy_matrix(adj, create_using=nx.DiGraph())

    # relabel nodes
    curr_nodes = new_graph.nodes()
    # flatten to row vector, convert to list of list extract first list element
    l = labels.ravel().tolist()   
    mapping = dict(zip(curr_nodes, l))

    new_graph=nx.relabel_nodes(new_graph,mapping)

    return new_graph
