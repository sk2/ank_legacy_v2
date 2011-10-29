"""
Loads configuration settings and creates logger
"""

import sys
# Supress DeprecationWarning in Python 2.6
if sys.version_info[:2] == (2, 6):
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

import pkg_resources
import os

#**************************************************************
# Settings
import ConfigParser
settings = ConfigParser.RawConfigParser()
#TRY with defaults
# TODO: better way to handle defaults
if os.path.isfile("autonetkit.cfg"):
    settings.read('autonetkit.cfg')
else:
    # load defaults
    default_cfg = pkg_resources.resource_filename(__name__,"/lib/autonetkit.cfg")
    settings.read(default_cfg)

ank_main_dir = settings.get('Lab', 'autonetkit_dir')

if not os.path.isdir(ank_main_dir):
    os.mkdir(ank_main_dir)

lab_dir = settings.get('Lab', 'netkit_dir')
lab_dir = os.path.join(ank_main_dir, lab_dir)

cbgp_dir = settings.get('Lab', 'cbgp_dir')
cbgp_dir = os.path.join(ank_main_dir, cbgp_dir)

gns3_dir = settings.get('Lab', 'gns3_dir')
gns3_dir = os.path.join(ank_main_dir, gns3_dir)

junos_dir = settings.get('Lab', 'junos_dir')
junos_dir = os.path.join(ank_main_dir, junos_dir)

plot_dir = settings.get('Lab', 'plot_dir')
plot_dir = os.path.join(ank_main_dir, plot_dir)

log_dir = os.path.join(ank_main_dir, "logs")
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)

plot_dir = os.path.join(ank_main_dir, "plots")
if not os.path.isdir(plot_dir):
    os.mkdir(plot_dir)


# Cache directory for templates
ank_dir = os.path.expanduser("~") + os.sep + ".autonetkit"
if not os.path.exists(ank_dir):
    os.mkdir(ank_dir)
template_cache_dir = ank_dir + os.sep + "cache"
if not os.path.exists(template_cache_dir):
    os.mkdir(template_cache_dir)

if (os.path.exists(template_cache_dir)
    and not os.access(template_cache_dir, os.W_OK)):
    LOG.info("Unable to write to cache dir %s, "
             "template caching disabled" % template_cache_dir)
    template_cache_dir = None


def add_logging(console_debug=False):
    import logging
    import logging.handlers

    LEVELS = {'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL}


#TODO: load logger settings from config file
    logger = logging.getLogger("ANK")
    logger.setLevel(logging.DEBUG)

#TODO: check settings are being loaded from file correctly
# and that handlers are being correctly set - as default level appearing

    ch = logging.StreamHandler()
    if console_debug:
        level = logging.DEBUG # User specified debug level
    else:
# Use debug from settings
        level = LEVELS.get(settings.get('Logging', 'console'))

    if level == logging.DEBUG:
# Include module name in debugging output
        formatter = logging.Formatter('%(module)s\t %(levelname)-6s %(message)s')
    else:
        formatter = logging.Formatter('%(levelname)-6s %(message)s')


    ch.setLevel(level)
    #ch.setLevel(logging.INFO)

    ch.setFormatter(formatter)

    logging.getLogger('').addHandler(ch)

    LOG_FILENAME =  os.path.join(log_dir, "autonetkit.log")
    LOG_SIZE = 2097152 # 2 MB
    fh = logging.handlers.RotatingFileHandler(
                LOG_FILENAME, maxBytes=LOG_SIZE, backupCount=5)

    level = LEVELS.get(settings.get('Logging', 'file'))

    fh.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s "
                                "%(funcName)s %(message)s")
    fh.setFormatter(formatter)

    logging.getLogger('').addHandler(fh)
