import sys                 
import os
import optparse    
import sys
from AutoNetkit.internet import Internet
import time    

import logging
# Can only get ANK logger after have imported Internet from ANK
LOG = logging.getLogger("ANK")

def main():
    # make it easy to turn on and off plotting and deploying from command line 
    opt = optparse.OptionParser()
    opt.add_option('--plot', '-p', action="store_true", dest="plot", 
                   default=False, help="Plot lab")
    opt.add_option('--deploy', '-d', action="store_true", dest="deploy", 
                   default=False, help="Deploy lab to Netkit host")
    opt.add_option('--file', '-f', default= None, 
                   help="Load configuration from FILE")        
    opt.add_option('--netkithost', '-n', default=None,
                   help="Netkit host machine (if located on another machine)") 
    opt.add_option('--username', '-u', default=None, 
                   help=("Username for Netkit host machine (if connecting to "
                   " external Netkit machine)"))
    opt.add_option('--verify', '-v', action="store_true", dest="verify",
                   default=False, help="Verify lab on Netkit host")      

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
          
    #### Main code 
    if not options.file:
        LOG.warn("Please specify topology file")
        sys.exit(0)
                
    f_name = options.file  
    # check exists
    if os.path.isfile(f_name):
        inet = Internet(tapsn = options.tapsn)
        inet.load(f_name)
    else:    
        #TODO: use logger
        print("Topology file {0} not found".format(f_name))
        sys.exit(0)
  
    inet.add_dns()

    inet.compile() 

    #inet.save()      

    if(options.plot):  
        inet.plot()      

    if(options.deploy):
        inet.deploy(host = options.netkithost, username = options.username,
                   xterm = options.xterm)     


    if(options.verify):
        inet.verify(host = options.netkithost, username = options.username)    
                  
if __name__ == "__main__": 
    main()
