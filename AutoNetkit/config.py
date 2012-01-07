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
import pprint
import logging
import validate


"""TODO:
    Document that configs files in (order of overwriting)
    (internal)
    ~/.autonetkit/autonetkit.cfg (check for Windows)
    ./autonetkit.cfg
    """

#**************************************************************
# Settings
import ConfigParser
settings = ConfigParser.RawConfigParser()

ank_user_dir = os.path.expanduser("~") + os.sep + ".autonetkit"
from configobj import ConfigObj, flatten_errors

# load defaults
spec_file = pkg_resources.resource_filename(__name__,"/lib/configspec.cfg")
settings = ConfigObj(configspec=spec_file, encoding='UTF8')

# Try in ~/.autonetkit/autonetkit.cfg
user_config_file = os.path.join(ank_user_dir, "autonetkit.cfg")
settings.merge(ConfigObj(user_config_file))

#TODO: look at using configspec validation

# also try from current directory
settings.merge(ConfigObj("autonetkit.cfg"))

pprint.pprint(settings)

validator = validate.Validator()
results = settings.validate(validator)
if results != True:
    print "Error loading configuration file:"
    for (section_list, key, _) in flatten_errors(settings, results):
        if key is not None:
            print 'Invalid key "%s" in section "%s"' % (key, ', '.join(section_list))
        else:
            print 'The following section was missing:%s ' % ', '.join(section_list)

    sys.exit(0)

#pprint.pprint(settings)
#pprint.pprint(settings['Netkit Hosts'])
#pprint.pprint(settings['Olive Hosts'])

ank_main_dir = settings['Lab']['autonetkit_dir']

if not os.path.isdir(ank_main_dir):
    os.mkdir(ank_main_dir)

"""TODO: tidy these up, make relative and absolute - just the extension and then the bit with ank_main_dir in it also
 so ensure consistent across compilers, deployment, etc
"""
lab_dir = settings['Lab']['netkit_dir']
lab_dir = os.path.join(ank_main_dir, lab_dir)

cbgp_dir = settings['Lab']['cbgp_dir']
cbgp_dir = os.path.join(ank_main_dir, cbgp_dir)

dynagen_dir = settings['Lab']['dynagen_dir']
dynagen_dir = os.path.join(ank_main_dir, dynagen_dir)

junos_dir = settings['Lab']['junos_dir']
junos_dir = os.path.join(ank_main_dir, junos_dir)

plot_dir = settings['Lab']['plot_dir']
plot_dir = os.path.join(ank_main_dir, plot_dir)

log_dir = os.path.join(ank_main_dir, "logs")
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)

plot_dir = os.path.join(ank_main_dir, "plots")
if not os.path.isdir(plot_dir):
    os.mkdir(plot_dir)

pickle_dir = os.path.join(ank_main_dir, "snapshots")
if not os.path.isdir(pickle_dir):
    os.mkdir(pickle_dir)

collected_data_dir = os.path.join(ank_main_dir, "collected_data")

def add_logging(console_debug=False):
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
        level = LEVELS.get(settings['Logging']['Console']['Level'])

    format_string = '%(levelname)-6s %(message)s'
    if level == logging.DEBUG:
# Include module name in debugging output
        format_string = "%(module)s\t" + format_string
    if settings['Logging']['Console']['Timestamp']:
        format_string = "%(asctime)s " + format_string

    formatter = logging.Formatter(format_string)

    ch.setLevel(level)
    #ch.setLevel(logging.INFO)

    ch.setFormatter(formatter)

    logging.getLogger('').addHandler(ch)

    LOG_FILENAME =  os.path.join(log_dir, "autonetkit.log")
    LOG_SIZE = 2097152 # 2 MB
    fh = logging.handlers.RotatingFileHandler(
                LOG_FILENAME, maxBytes=LOG_SIZE, backupCount=5)

    level = LEVELS.get(settings['Logging']['File']['Level'])

    fh.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s "
                                "%(funcName)s %(message)s")
    fh.setFormatter(formatter)

    logging.getLogger('').addHandler(fh)

LOG = logging.getLogger("ANK")

# Cache directory for templates
if not os.path.exists(ank_user_dir):
    os.mkdir(ank_user_dir)
template_cache_dir = ank_user_dir + os.sep + "cache"
if not os.path.exists(template_cache_dir):
    os.mkdir(template_cache_dir)

if (os.path.exists(template_cache_dir)
    and not os.access(template_cache_dir, os.W_OK)):
    LOG.info("Unable to write to cache dir %s, "
             "template caching disabled" % template_cache_dir)
    template_cache_dir = None
