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
    usage = ("\nNetkit: %prog\n"
            "Additional documentation at http://packages.python.org/AutoNetkit/")
    opt = optparse.OptionParser(usage, version="%prog " + str(version))
    opt.add_option('--debug',  action="store_true", default=False, help="Debugging output")
    opt.add_option('--count',  type="int", default=1, help="Number of times to run collect")
    opt.add_option('--delay',  type="int", default=0, help="Delay between each iteration")

    options, arguments = opt.parse_args()
    config.add_logging(console_debug = options.debug)
            
#### Main code 

    inet = Internet()

    inet.restore()
    inet.collect_data(count=options.count, delay=options.delay)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
