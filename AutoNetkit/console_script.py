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
    opt.add_option('--deploy', action="store_true", default=False, help="Deploy lab to hosts")
    opt.add_option('--verify', action="store_true", default=False, help="Verify lab on hosts")
    opt.add_option('--save', action="store_true", default=False, 
            help="Save the network for future use (eg verification")
    opt.add_option('--file', '-f', default= None, 
                    help="Load configuration from FILE")        
    opt.add_option('--bgp_policy', default= None, 
                    help="Load BGP policy statements from FILE")     

    opt.add_option('--debug',  action="store_true", default=False, help="Debugging output")

# Deployment environments
    opt.add_option('--netkit',  action="store_true", default=False, help="Compile Netkit")
    opt.add_option('--cbgp',  action="store_true", default=False, help="Compile cBGP")
    opt.add_option('--dynagen',  action="store_true", default=False, help="Compile dynagen")
    opt.add_option('--junos',  action="store_true", default=False, help="Compile Junosphere  (legacy command)")
# Juniper options
    opt.add_option('--junosphere',  action="store_true", default=False, help="Compile to Junosphere")
    opt.add_option('--junosphere_olive',  action="store_true", default=False, 
            help="Compile to Olive-based Junosphere")
    opt.add_option('--olive',  action="store_true", default=False, help="Compile to Qemu-based Olive")
    opt.add_option('--olive_qemu_patched',  action="store_true", default=False, 
            help="Custom Qemu install (6 interface count")
    opt.add_option('--isis',  action="store_true", default=False, help="Use IS-IS as IGP")
    opt.add_option('--ospf',  action="store_true", default=False, help="Use OSPF as IGP")

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
#TODO: handle this properly using default arguments
    igp = "ospf"
    if options.isis:
        igp = "isis"

    use_junosphere = (options.junos or options.junosphere)
    inet = Internet(netkit=options.netkit,
            cbgp=options.cbgp, dynagen=options.dynagen, junosphere=use_junosphere,
            junosphere_olive=options.junosphere_olive, olive=options.olive, 
            policy_file = options.bgp_policy,
            olive_qemu_patched=options.olive_qemu_patched, igp=igp)
    inet.load(f_name)

    inet.add_dns()

    inet.compile() 

#inet.save()      

    if(options.plot):  
        inet.plot()      

    if(options.deploy):
        inet.deploy()     

    if options.verify:
        inet.verify()

    # finally, save the network
    if options.save:
        inet.save()
    #inet.restore()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
