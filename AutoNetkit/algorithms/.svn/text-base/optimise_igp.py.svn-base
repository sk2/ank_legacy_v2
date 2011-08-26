from __future__ import division


"""
Simple version of IGP weight optimisation using a Genetic Algorithm  
See [1]
[1] M. Ericsson, M.G.C. Resende, and P.M. Pardalos. A genetic algorithm 
for the weight setting problem in OSPF routing. 
Journal of Combinatorial Optimization, 6:299-333, 2002.

"""
__author__ = """\n""".join(['Simon Knight (simon.knight@adelaide.edu.au)',
                            'Hung Nguyen (hung.nguyen@adelaide.edu.au)'])
#    Copyright (C) 2009-2010 by 
#    Simon Knight  <simon.knight@adelaide.edu.au>
#    Hung Nguyen  <hung.nguyen@adelaide.edu.au>
#    All rights reserved.
#    BSD license.
#



# do standard floating division as per 
# http://www.ferg.org/projects/python_gotchas.html#contents_item_3

import networkx as nx
from random import random, randint

import logging
LOG = logging.getLogger("ANK")

import pprint   
pp = pprint.PrettyPrinter(indent=4)

# Can set seed so keep same result each time it is run
#seed(234929384)  


#TODO: this currently works on a per-AS basis. Integrate with multi-AS network
                    
huge = 1e16                

class OptimiseIGP:  

    #TODO: make work on a network object rather than a graph
    
    def __init__(self, network, traffmat = None, max_link_changes = huge):
        # max_changes by default is a huge number, cost becomes a very
        # large number if more than this number of changes to the 
        # original weights occurs
        self.traffmat = traffmat
        self.G = graph 
       
        #TODO: see if this has any effect, as deepcopy is needed for edge data
        self.G_original = graph.copy()   
        
        # Get weights of the set graph
        original_weights = self.weights()
        
        # Store the weights of the set graph, used to compare how many 
        # link weights have been changed
        self.original_weights = original_weights 
        
        self.max_link_changes = max_link_changes  
        
    def __str__(self):
        return str(self.G) 
        
    def link_changes_cost(self, individual):
        if(self.max_link_changes >= huge ): 
            # No max link changes set, so no cost of changing links
            return 0                                          
        else:     
            # see how different individual is from the original weights
            #TODO: rewrite as a list comprehension
            diff_list = filter( lambda x: x not in individual, 
                               self.original_weights)  
            diff_count = len(diff_list)  
            if(diff_count > self.max_link_changes): 
                # More link changes than allowed, return a huge number
                return huge
            else:
                # Note: this return value can be tweaked, depending on 
                # desired relative emphasis of link changes
                return 10*diff_count

    def set_traffic_matrix(self, traffmat):
        self.traffmat = traffmat  
    
    def weights(self):
        #returns list of weights for edges in graph
        #assumes positions/order from edge iteration                 
        return [e[2]['weight'] for e in self.G.edges(data = True)]
              
    
    def set_weights(self, w_list):    
        #TODO: rewrite this using a map operator
        # see how often used if worth it
        for i, edge in enumerate(self.G.edges_iter()):
            #s = e[0], t=e[1], weight=e[2]['weight'] etc
            self.G[e[0]][e[1]]['weight'] = w_list[i]  
        
    #population is a list of weight lists
    #GA code based on 
    #lethain.com/entry/2009/jan/02/genetic-algorithms-cool-name-damn-simple/
    def population(self, count, length, min_val, max_val):     
        return [ self.individual(length, min_val, max_val) 
                for x in xrange(count) ]

    def individual(self, length, min_val, max_val):   
        return [ randint(min_val, max_val) for x in xrange(length) ]

    def fitness(self, individual): 
        # init capacities 
        default_speed = 100
        for src, dst in [ (src, t) for (src, t, data) 
                         in self.G.edges(data = True)
                         if 'speed' not in data]:
            self.G[src][dst]['speed'] = default_speed
        
        # Copy list to pop
        weights = individual[:]
        # set weights
        #TODO: look at using set_weights function
        for (src, dst) in self.G.edges(): 
            #TODO: check order - whether this is forwards or backwards
            # if weights already set         
            #FIX check this!
            self.G[src][dst]['weight'] = weights.pop()
        
        # Cost is sum of network cost (from traffic on links) and link changes 
        # cost (how many links changed from original weights)
        #TODO look at link change costs
        link_change_cost = self.link_changes_cost(individual) 
        if(link_change_cost >= huge):
            # Cost is already a huge number, return
            # (saves expensive computation of network traffic)
            return link_change_cost
                    
        # get edge list to store weights in
        loads = nx.to_dict_of_dicts(self.G, edge_data = 0)
        
        apsf = nx.all_pairs_dijkstra_path(self.G)
        for src, data in apsf.items():    
            for dst, path in data.items():        
                # load from this source, dest pair
                load = self.traffmat[src][dst] 
                for (nodea, nodeb) in zip(path, path[1:]):
                    # add load on this edge due to source, dest pair
                    loads[nodea][nodeb] += load
        
        def cost(load, cap):
            #Cost is set according to equation (1) of [1]
            utilization = load/cap

            if utilization < 1/3:
                return utilization
            elif utilization < 2/3:
                return 3*utilization-2/3 
            elif utilization < 9/10:
                return 10*utilization-16/3 
            elif utilization < 1:
                return 70*utilization-178/3
            elif utilization < 11/10:
                return 500*utilization-1468/3
            else:
                return 5000*utilization-16318/3
        

        # link change cost was a low number, calculate network traffic cost  
        # calculate cost for each edge that has a load set  
        link_costs = [ cost(loads[s][t], data['speed']) for (s, t, data) 
                      in self.G.edges(data = True) ] 
        
        link_costs = sum(link_costs)
        #link_costs = sum(link_costs)
        #print  "cost total {0}".format(link_costs)
        return link_change_cost + link_costs

            
    def evolve(self, pop, retain = 0.5, random_select = 0.4, 
               mutate = 0.4, min_val = 0, max_val = 100):
        graded = pop                  
        
        # retain is the number of entries to retain 
        
        #TODO: check mutating correctly
    
        #prepend fitness to start of each entry
        graded = [ (self.fitness(x), x) for x in pop]            
        #print graded
        #sort based on 1st element (fitness), retain only 2nd element (indiv) 
        LOG.debug("Best individual is {0:.2f}".format(graded[0][0], 2))

        graded = [ x[1] for x in sorted(graded)]     
    
        #work out how many entries to retain
        retain_length = int(len(graded)*retain)
        #truncate up to the amount we want to retain
        parents = graded[:retain_length]
        
        # randomly add other individuals to promote genetic diversity
        for individual in graded[retain_length:]:
            #amount to add in is also random
            if random_select > random():  
                parents.append(individual)  
            
        # mutate some individuals (but not the best)
        for individual in parents[1:len(parents)]:
            if mutate > random():       
                pos_to_mutate = randint(0, len(individual)-1)  
                individual[pos_to_mutate] = randint(min_val, max_val)
           
        # crossover parents to create children
        parents_length = len(parents)
        #how many children to create
        desired_length = len(pop) - parents_length
        children = []
        while len(children) < desired_length:
            male = randint(0, parents_length-1)
            female = randint(0, parents_length-1)
            if male != female:
                male = parents[male]
                female = parents[female]
                #random split point rather than 50:50 split
                split = int(len(male) * random())
                child = male[:split] + female[split:]
                children.append(child)
        parents.extend(children)

        return parents

    def grade(self, pop):  
        #find average fitness for a population
        total = 0
        for x in pop:
            total += self.fitness(x)
        return total / (len(pop) * 1.0)  
        
    def optimise(self, pop_length = 50, iterations = 25, 
                 min_val = 1, max_val = 500):
        #This function does all the work, calls the other functions         
        cur_weights = self.weights()     
        
        if(self.original_weights != None): 
            # Check for trivial case, when all original weights are 1 (default) 
            #ie length = sum (is true if only contains ones)
            if(sum(self.original_weights) == len(self.original_weights)):     
                # Warn that will randomise 
                LOG.warn(("Set weights are trivial (all ones). Randomising "
                             " weights before optimising."))
                # Generate random population
                pop = self.population(pop_length, len(cur_weights), min_val,
                                      max_val)
                # Set max link changes 
                self.max_link_changes = huge   
            else:
                # create initial population of original weights
                pop = [self.original_weights for i in range(0, pop_length)]  
        else:
            # Randomly generate initial population  
            pop = self.population(pop_length, len(cur_weights), min_val,
                                  max_val) 
        
        
        for i in range(1, iterations):  
            LOG.debug("Optimisation iteration {0}/{1}".format(i, iterations))
            pop = self.evolve(pop, min_val = min_val, max_val = max_val)
        
        # Best entry is the top after sorting
        graded = [ (self.fitness(x), x) for x in pop]
        graded = [ x[1] for x in sorted(graded)]
        best = graded[0]

        # Set graph with best entry
        self.set_weights(best)
        # and return result
        return self.G  
    
    def generate_traffic_matrix(self, min_val = 0, max_val = 100):
        # Generates a traffic matrix based on G
        # Results stored in dictionary (indexed on router hash)    

        #TODO: make as a numpy matrix, zero diagonals, and then convert to dict
        traffmat = {}
        for i, src in enumerate(self.G.nodes_iter()):
            traffmat[s] = {}
            for j, dst in enumerate(self.G.nodes_iter()):
                if(i == j):      
                    # No traffic to self
                    traffmat[src][dst] = 0
                else:
                    traffmat[src][dst] = randint(min_val, max_val)
        return traffmat
