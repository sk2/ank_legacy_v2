"""
**********
PathDrawer
**********

Draw multiple paths in a graph. Uses matplotlib (pylab).

The path corners are rounded with the help of cube Bezier curves.

If two or more paths traverse the same edge, they are automatically shifted to make them all visible. 


References:
 - matplotlib:     http://matplotlib.sourceforge.net/
 - Bezier curves:  http://matplotlib.sourceforge.net/api/path_api.html
 
"""

__author__ = """Maciej Kurant (maciej.kurant@epfl.ch)"""
#    Copyright (C) 2008 by
#    Maciej Kurant <maciej.kurant@epfl.ch>
#    Distributed under the terms of the GNU Lesser General Public License
#    http://www.gnu.org/copyleft/lesser.html

__all__ = ['is_valid_edge_path',
           'is_valid_node_path',
           'to_node_path',
           'to_edge_path',
           'normalize_layout',
           'draw_path',
           'draw_many_paths']



try:
    import matplotlib
    import matplotlib.path
except ImportError:
    raise ImportError, "Import Error: not able to import matplotlib."
except RuntimeError:
    pass # unable to open display

MPath=matplotlib.path.Path


import numpy
import random
import math





#####################
def is_valid_edge_path(path, G):
    '''Returns True if path consists of consecutive edges in G, and False otherwise.'''
    if len(path)==0: return True
    for i in range(len(path)-1):
        try:
            if len(path[i])<2 or len(path[i+1])<2: return False
        except TypeError:   # no len() specified, e.g., an integer
            return False
        if path[i][1]!=path[i+1][0]: return False
        if not G.has_edge(*path[i]): return False
    if not G.has_edge(*path[-1]): return False
    return True


#####################
def is_valid_node_path(path, G):
    '''Returns True if path is valid in G, and False otherwise.'''
    if len(path)<2: return False
    for i in range(len(path)-1):
        if not G.has_edge(path[i],path[i+1]): return False
    return True


#####################
def to_node_path(edge_path):
    'E.g., [(10, 3), (3, 6), (6, 11)] -> [10,3,6,11]'
    np = [e[0] for e in edge_path]
    np.append(edge_path[-1][1])
    return np

#####################
def to_edge_path(path, G=None):
    '''Converts a node_path to edge_path, e.g., [10,3,6,11] -> [(10, 3), (3, 6), (6, 11)]

    If G is given, then the path validity is checked. Then 'path' is tolerated to be
    also an edge_path; in this case it is returned directly. 
    '''
    if G==None:
        return [(path[i],path[i+1])  for i in range(len(path)-1)]
    if is_valid_node_path(path,G):
        return to_edge_path(path)
    else:
        if not is_valid_edge_path(path,G): raise ValueError('Not a valid path:\npath='+str(path))
        return path


#####################
def vector_length(v):
    '''Returns the length of vector v=numpy.array([x,y]).'''
    return math.sqrt(numpy.dot(v,v))
   

#####################
def norm_vector(v):
    '''Returns a vector numpy.array([x,y]) of length 1, pointing in the same
    direction as v = numpy.array([x0,y0]) .'''

    l=vector_length(v)
    if l==0.: raise ValueError('Vector v='+str(v)+' has length 0 !')
    return v/l

#####################
def perpendicular_vector(v):
    '''Returns a vector numpy.array([x,y]) perpendicular to v.'''
    return numpy.array([v[1],-v[0]])


#####################
def crossing_point(p1a, p1b, p2a, p2b):
    '''Returns the crossing of line1 defined by two points p1a and p1b, and line2 defined by two points p2a, p2b.
    All points should be of format numpy.array([x,y]).
    If line1 and line2 are parallel then returns None.
    '''
    # See e.g.: http://stackoverflow.com/questions/153592/how-do-i-determine-the-intersection-point-of-two-lines-in-gdi
    
    if tuple(p1a)==tuple(p1b) or tuple(p2a)==tuple(p2b): raise ValueError('Two points defining a line are identical!')
    v1 = p1b-p1a
    v2 = p2b-p2a
    x12 = p2a-p1a
    D =  numpy.dot(v1,v1)*numpy.dot(v2,v2) - numpy.dot(v1,v2) * numpy.dot(v1,v2)
    if D==0:  return None     # Lines are parallel!
    
    a = (numpy.dot(v2,v2) * numpy.dot(v1,x12) - numpy.dot(v1,v2) * numpy.dot(v2,x12)) / D
    return p1a + v1*a


#####################
def is_layout_normalized(pos):
    'True if points in pos stay within (0,0) x (1,1)'
    A = numpy.asarray(pos.values())
    if min(A[:,0])<0 or min(A[:,1])<0 or max(A[:,0])>1 or max(A[:,1])>1:
        return False
    return True

#####################
def normalize_layout(pos):
    '''All node positions are normalized to fit in the unit area (0,0)x(1,1).'''
    if len(pos)==1:
        v=pos.keys()[0]
        pos[v]= numpy.array([0.5,0.5])
        return
    A=numpy.asarray(pos.values())
    x0,y0,x1,y1  =  min(A[:,0]),min(A[:,1]),max(A[:,0]),max(A[:,1])
    for v in pos:
        pos[v] = (pos[v]-(x0,y0))/(x1-x0,y1-y0)*0.8+(0.1,0.1)
    return


#####################
def draw_path(G, pos, path, shifts=None, color='r', linestyle='solid', linewidth=1.0):
    '''Draw a path 'path' in graph G.

    Parameters
    ----------
    pos :       a node layout used to draw G. Must be normalized to (0,0)x(1,1),
                e.g., by function normalize_layout(pos)
    path :      edge_path or node_path
    shifts :    a list of length len(edge_path) specifying how far the path
                must be drawn from every edge it traverses.
    color :     e.g., one out of ('b','g','r','c','m','y').
    linestyle : one out of ('solid','dashed','dashdot','dotted')
    linewidth : float, in pixels


    Examples
    --------
    >>> g=networkx.krackhardt_kite_graph()
    >>> pos=networkx.drawing.spring_layout(g)
    >>> normalize_layout(pos)
    >>> networkx.draw(g,pos)
    >>> path = networkx.shortest_path(g, 3, 9)
    >>> draw_path(g, pos, path, color='g', linewidth=2.0)
    >>> matplotlib.pyplot.show()
    
    '''

    if not is_layout_normalized(pos):   raise ValueError('Layout is not normalized!')
    edge_path = to_edge_path(path, G)
    if len(edge_path)==0: return
    
    if shifts==None:  shifts = [0.02] * len(edge_path)
    if len(shifts)!=len(edge_path): raise ValueError("The argument 'shifts' does not match 'edge_path'!")

    # edge_pos      - positions of edges
    # edge_shifts   - shifts of edges along a perpendicular vectors; the shifting distance is determined by 'shifts'
    edge_pos = [numpy.array([pos[e[0]],pos[e[1]]]) for e in edge_path]
    edge_shifts = [ shifts[i]*perpendicular_vector(norm_vector(p1b-p1a)) for i,(p1a,p1b) in enumerate(edge_pos)]

      
    # prepare vertices and codes for object matplotlib.path.Path(vertices, codes) - the path to display
    # vertices: an Nx2 float array of vertices  (not the same as graph nodes!)
    # codes: an N-length uint8 array of vertex types (such as MOVETO, LINETO, CURVE4)  - a cube Bezier curve
    # See e.g. http://matplotlib.sourceforge.net/api/path_api.html

    # First, for every corner (node on the path), we define 4 points to smoothen it
    corners=[]
    
    #The first 'corner' - on a straight line, easier to process next
    p1a,p1b = edge_pos[0] + edge_shifts[0] 
    V1=p1b-p1a
    corners.append([p1a, p1a+0.1*V1, p1a+0.1*V1, p1a+0.2*V1])      
   
    #All real corners - with edes on both sides
    for i in range(len(edge_pos)-1):
        p_node = edge_pos[i][1]                             # crossing point of the original (i)th and (i+1)th edges 
        p1a,p1b = edge_pos[i] + edge_shifts[i]              # two points defining the shifted (i)th edge 
        p2a,p2b = edge_pos[i+1] + edge_shifts[i+1]          # two points defining the shifted (i+1)th edge
        V1 = norm_vector(p1b - p1a)                         # unit vector along the (i)th edge
        V2 = norm_vector(p2b - p2a)                         # unit vector along the (i+1)th edge
        p_middle_angle = p_node + (V2-V1)                   # a point that splits evenly the angle between the original (i)th and (i+1)th edges
        c12 = crossing_point(p1a, p1b, p2a, p2b)            # crossing point of the shifted (i)th and (i+1)th edges
        if c12==None:   # the edges are parallel
            c12 = (p1b+p2a)/2
            p_middle_angle = c12
        c1 = crossing_point(p1a,p1b,p_node,p_middle_angle)  # crossing point of the shifted (i)th edge and the middle-angle-line
        c2 = crossing_point(p2a,p2b,p_node,p_middle_angle)  # crossing point of the shifted (i+1)th edge and the middle-angle-line
        D= 0.5*(shifts[i]+shifts[i+1])                      # average shift - a reasonable normalized distance measure
        
        if vector_length(p_node-c12) < 2.5*D:               # if the crossing point c12 is 'relatively close' to the node
            corners.append([c12-D*V1, c12, c12, c12+D*V2])  # then c12 defines two consecutive reference points in the cube Bezier curve
        else:                                               # the crossing point c12 is NOT 'relatively close' to the node
            P1=p1b + D*V1
            if numpy.dot(c1-P1, V1)<0:    P1=c1
            P2=p2a - D*V2
            if numpy.dot(c2-P2, V2)>0:    P2=c2
            corners.append([P1-D*V1, P1, P2, P2+D*V2])

    #The last 'corner' -  on one line, easier to process next
    p1a,p1b = edge_pos[-1] + edge_shifts[-1] 
    V1=p1b-p1a
    corners.append( [p1b-0.2*V1, p1b-0.1*V1, p1b-0.1*V1, p1b] )    
 
    # Now, based on corners, we prepare vertices and codes
    vertices=[]
    codes = []
    # First operation must be a MOVETO, move pen to first vertex on the path
    vertices += [corners[0][0]]
    codes += [MPath.MOVETO]

    for i,corner in enumerate(corners):

        # If there is not enough space to draw a corner, then replace the last two vertices from the previous section, by the last two vertives of the current section
        if i>0:  
            if vector_length(norm_vector(corner[0]-vertices[-1]) - norm_vector(corner[1]-corner[0]))>1:  
                vertices.pop();
                vertices.pop();
                vertices += corner[-2:]
                continue
        
        codes+=[MPath.LINETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4]
        vertices+=corner

    # Finally, create a nice path and display it
    path = MPath(vertices, codes)
    patch = matplotlib.patches.PathPatch(path, edgecolor=color, linestyle=linestyle, linewidth=linewidth, fill=False, alpha=1.0)
    ax=matplotlib.pylab.gca()
    ax.add_patch(patch)
    ax.update_datalim(((0,0),(1,1)))
    ax.autoscale_view()

    return
    

#####################
def draw_many_paths(G, pos, paths, max_shift=0.02, linewidth=2.0):
    '''Draw every path in 'paths' in graph G.
    Colors and linestyles are chosen automatically.
    All paths are visible - no path section can be covered by another path.

    Parameters
    ----------
    pos :       a node layout used to draw G. Must be normalized to (0,0)x(1,1),
                e.g., by function normalize_layout(pos)
    paths :     a collection of node_paths or edge_paths
    max_shift : maximal distance between an edge and a path traversing it.
    linewidth : float, in pixels.

    Examples
    --------
    >>> g=networkx.krackhardt_kite_graph()
    >>> g.remove_node(9)
    >>> path1 = networkx.shortest_path(g, 2, 8)
    >>> path2 = networkx.shortest_path(g, 0, 8)
    >>> path3 = [(1,0),(0,5),(5,7)]                 # edge_path
    >>> path4 = [3,5,7,6]                           # node_path
    >>> pos=networkx.drawing.spring_layout(g)
    >>> normalize_layout(pos)
    >>> networkx.draw(g,pos, node_size=140)
    >>> draw_many_paths(g, pos, [path1, path2, path3, path4], max_shift=0.03)    
    >>> matplotlib.pyplot.show()
    
    '''
    
    if len(paths)==0: return
    if not is_layout_normalized(pos): raise ValueError('Layout is not normalized!')
        
    edge_paths=[to_edge_path(path,G) for path in paths]
    edge_paths.sort(key=len, reverse=True)   # Sort edge_paths from the longest to the shortest

    
    # Find the largest number of edge_paths traversing the same edge and set single_shift accordingly
    edge2count = {}
    for path in edge_paths:
        for e in path:
            edge2count[e] = edge2count.get(e,0) + 1
    single_shift = max_shift/max(edge2count.values())

    # Draw the edge_paths by calling draw_path(...). Use edge2shift to prevent the path overlap on some edges.
    colors=('b','g','r','c','m','y')
    linestyles=('solid','dashed','dashdot','dotted')
    edge2shift={}
    for i,path in enumerate(edge_paths):
        shifts=[ edge2shift.setdefault(e, single_shift)  for e in path]      
        draw_path(G, pos, path, color=colors[i%len(colors)], linestyle=linestyles[i/len(colors) % len(linestyles)], linewidth=linewidth, shifts=shifts)
        for e in path:   edge2shift[e] += single_shift

    return 



##########################################
if __name__ == "__main__":

    # Example
    
    import networkx

    g=networkx.krackhardt_kite_graph()
    g.remove_node(9)
    path1 = networkx.shortest_path(g, 2, 8)
    path2 = networkx.shortest_path(g, 0, 8)
    path3 = [(1,0),(0,5),(5,7)]
    path4 = [3,5,7,6]
    pos=networkx.drawing.spring_layout(g)
    normalize_layout(pos)
    networkx.draw(g,pos, node_size=140)
    draw_many_paths(g, pos, [path1, path2, path3, path4], max_shift=0.03)
    matplotlib.pyplot.savefig("PathDrawer.png") 
    matplotlib.pyplot.show()

    
