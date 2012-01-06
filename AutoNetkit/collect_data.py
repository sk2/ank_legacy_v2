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

    options, arguments = opt.parse_args()
    config.add_logging(console_debug = options.debug)
            
#### Main code 

    inet = Internet()

    inet.restore()
    inet.collect_data()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
