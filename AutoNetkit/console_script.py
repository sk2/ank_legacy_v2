#!/usr/bin/env python


"""Standalone console script"""

import sys
import os
import optparse

from AutoNetkit.internet import Internet
from AutoNetkit import config
import AutoNetkit as ank
import logging
import pkg_resources
LOG = logging.getLogger("ANK")

def main():

    version=pkg_resources.get_distribution("AutoNetkit").version
# make it easy to turn on and off plotting and deploying from command line 
    usage = ("\nNetkit: %prog -f filename.graphml --netkit\n"
            "Junosphere: %prog -f filename.graphml --junos\n"
            "Additional documentation at http://packages.python.org/AutoNetkit/")
    opt = optparse.OptionParser(usage, version="%prog " + str(version))

    opt.add_option('--plot', '-p', action="store_true", dest="plot", 
                    default=False, help="Plot lab")
    opt.add_option('--deploy', '-d', action="store_true", 
                    default=False, help="Deploy lab to Netkit host")
    opt.add_option('--file', '-f', default= None, 
                    help="Load configuration from FILE")        
    opt.add_option('--bgp_policy', default= None, 
                    help="Load BGP policy statements from FILE")     
    opt.add_option('--netkit_host', default=None,
                    help="Netkit host machine (if located on another machine)") 
    opt.add_option('--netkit_username', default=None, 
                    help=("Username for Netkit host machine (if connecting to "
                    " external Netkit machine)"))
    opt.add_option('--olive_host', default=None,
                    help="Olive host machine (if located on another machine)") 
    opt.add_option('--olive_username', default=None, 
                    help=("Username for Olive host machine (if connecting to "
                    " external Olive machine)"))
    opt.add_option('--olive_base_image', default=None, help=("Base image to use on Olive"))

    opt.add_option('--verify', '-v', action="store_true", dest="verify",
                    default=False, help="Verify lab on Netkit host")      

    opt.add_option('--xterm', action="store_true", dest="xterm",
                    default=False, help=("Load each VM console in Xterm "
                                        " This is the default in Netkit, "
                                        " but not ANK due to "
                                            "potentially large number of VMs"))
    opt.add_option('--dynagen_image',  default= None, help="Image to use for dynagen") 
    opt.add_option('--dynagen_hypervisor',  default= "localhost:7200", help="Hypervisor to use for dynagen") 

    opt.add_option('--debug',  action="store_true", default=False, help="Debugging output")

# Deployment environments
    opt.add_option('--netkit',  action="store_true", default=False, help="Compile Netkit")
    opt.add_option('--cbgp',  action="store_true", default=False, help="Compile cBGP")
    opt.add_option('--dynagen',  action="store_true", default=False, help="Compile dynagen")
# Juniper options
    opt.add_option('--junosphere',  action="store_true", default=False, help="Compile to Junosphere")
    opt.add_option('--junosphere_olive',  action="store_true", default=False, 
            help="Compile to Olive-based Junosphere")
    opt.add_option('--olive',  action="store_true", default=False, help="Compile to Qemu-based Olive")
    opt.add_option('--olive_qemu_patched',  action="store_true", default=False, 
            help="Custom Qemu install (6 interface count")
    opt.add_option('--isis',  action="store_true", default=False, help="Use IS-IS as IGP")
    opt.add_option('--ospf',  action="store_true", default=False, help="Use OSPF as IGP")

    opt.add_option('--tapsn', default="172.16.0.0/16", 
                help= ("Tap subnet to use to connect to VMs. Will be split into "
                        " /24 subnets, with first subnet allocated to tunnel VM. "
                        "eg 172.16.0.1 is the linux host, 172.16.0.2 is the "
                        " other end of the tunnel")) 

    options, arguments = opt.parse_args()
    config.add_logging(console_debug = options.debug)
            
#### Main code 
    if not options.file:
        LOG.warn("Please specify topology file")
        sys.exit(0)
        logging.setLevel(logging.DEBUG)

    if not (options.netkit or options.cbgp or options.dynagen or 
            options.junosphere or options.junosphere_olive or options.olive):
        LOG.warn("Please specify a target environment, eg --netkit")
        sys.exit(0)

    if ((options.junosphere or options.junosphere_olive or options.olive )
        and not (options.isis or options.ospf)):
        LOG.warn("Please specify an IGP if using junos: --isis or --ospf")
        sys.exit(0)
                
#TODO: if topology file doesn't exist, then try inside lib/examples/topologies/
    f_name = options.file  
# check exists
    if os.path.isfile(f_name):
        igp = "ospf"
        if options.isis:
            igp = "isis"
        inet = Internet(tapsn = options.tapsn, netkit=options.netkit,
                cbgp=options.cbgp, dynagen=options.dynagen, junosphere=options.junosphere,
                junosphere_olive=options.junosphere_olive, olive=options.olive, 
                policy_file = options.bgp_policy,
                olive_qemu_patched=options.olive_qemu_patched, igp=igp)
        inet.load(f_name)
    else:    
        LOG.warn("Topology file %s not found" % f_name)
        sys.exit(0)

    # set properties
    inet.dynagen_hypervisor = options.dynagen_hypervisor
    if options.dynagen_image:
        inet.dynagen_image = options.dynagen_image

    inet.add_dns()

    inet.compile() 

#inet.save()      

    if(options.plot):  
        inet.plot()      

    if(options.deploy):
        inet.deploy(netkit_host = options.netkit_host, netkit_username = options.netkit_username,
                olive_host = options.olive_host, olive_username = options.olive_username,
                olive_base_image = options.olive_base_image,
                xterm = options.xterm)     

    if(options.verify):
        inet.verify(host = options.netkithost, username = options.netkitusername)    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
