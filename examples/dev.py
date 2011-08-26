#!/usr/bin/env python


import sys                 
sys.path.append('..')
import time
                 
import optparse    


from AutoNetkit.internet import Internet

import time    
import networkx as nx    

        
# make it easy to turn on and off plotting and deploying from command line     
opt = optparse.OptionParser()
opt.add_option('--plot', '-p', action="store_true", dest="plot", 
               default=False, help="Plot lab")
opt.add_option('--deploy', '-d', action="store_true", dest="deploy", 
               default=False, help="Deploy lab to Netkit host")
opt.add_option('--verify', '-v', action="store_true", dest="verify",
               default=False, help="Verify lab on Netkit host")
opt.add_option('--file', '-f', default="examples/example.txt", 
               help="Load configuration from FILE")        
opt.add_option('--netkithost', '-n', default="netkithost",
               help="Netkit host machine (if located on another machine)")
opt.add_option('--username', '-u', default="autonetkit", 
               help= ("Username for Netkit host machine "
                      "(if connecting to external Netkit machine)"))

opt.add_option('--xterm', action="store_true", dest="xterm",
               default=False, help=("Load each VM console in Xterm "
                                    " This is the default in Netkit, "
                                    " but not ANK due to "
                                    "potentially large number of VMs"))

opt.add_option('--tapsn', default="172.16.0.0/16", 
               help= ("Tap subnet to use to connect to VMs. Will be split into "
                      " /24 subnets, with first subnet allocated to tunnel VM. "
                      "eg 172.16.0.1 is the linux host, 172.16.0.2 is the "
                      " other end of the tunnel")) 
options, arguments = opt.parse_args()

#TODO: write unit tests for ank and perhaps compile

#### Main code    
             
start = time.time()      

#TODO: change list comprehensions to use generator expressions
# look at http://www.python.org/dev/peps/pep-0289/
    
start = time.time()      

#inet = Internet("topologies/simple.yaml")      
#inet = Internet("topologies/aarnet.yaml")   

inet = Internet(tapsn = options.tapsn)

inet.load(options.file)

#inet.generate(10)

#myAS = inet.add_as(1234)        
#rA = myAS.add_router("A") 
#rB = myAS.add_router("B") 
#rC = myAS.add_router("C")  

# now some fancy stuff
#rD = rA * rB    
#print rD      
#rE = rD * rA
#print rE   

#test = rA.clone(count=5)
#print test

#myAS.add_link(rA, rB, {"weight": 10})
#myAS.add_link(rA, rC)
#myAS.add_link(rB, rC)
#
#inet.add_link("AS2rA", rC)   

#inet.duplicate_node(rC) 


inet.add_dns()

#inet.optimise()   
            
inet.compile() 
print "Lab compiled in {0} seconds".format(round(time.time() - start,3)) 

#inet.save()      

if(options.plot):  
    inet.plot()      
                                                                           
if(options.deploy):
    inet.deploy(host = options.netkithost, username = options.username,
               xterm = options.xterm)     

if(options.verify):
    inet.verify(host = options.netkithost, username = options.username,
                tapsn = options.tapsn)     





