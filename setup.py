#!/usr/bin/env python
from setuptools import setup
#from setuptools import setup, find_packages

setup (
     name = "AutoNetkit",
     version = "0.5.54",
     description = 'Automated configuration generator for cBGP, Netkit and Junosphere',
     long_description = 'Automated configuration generator for cBGP, Netkit and Junosphere',

     # simple to run 
     entry_points = {
         'console_scripts': [
             'autonetkit = AutoNetkit.console_script:main',
         ],
     },

     author = 'Simon Knight, Hung Nguyen',
     author_email = "simon.knight@adelaide.edu.au",
     url = "http://packages.python.org/AutoNetkit/",
     packages = ['AutoNetkit', 'AutoNetkit.algorithms', 'AutoNetkit.compiler',
         'AutoNetkit.tests', 'AutoNetkit.examples',
         'AutoNetkit.deploy', 'AutoNetkit.internal',
         'AutoNetkit.readwrite', 'AutoNetkit.plotting'],

     package_data = {'': ['settings.cfg', 'lib/templates/*/*.mako',
                          'lib/shadow', 'lib/autonetkit.cfg',
                          'lib/authorized_keys', 'plugins/*', 'plugins/*.py',
                          'algorithms/*.py', 'plotting/*.py', 'deploy/*.py',
                          'compiler/*.py', 'internal/*.py',
                          'examples/*.py',
                          'test/*,py',
                          'readwrite/*.py']},
     download_url = ("http://pypi.python.org/pypi/AutoNetkit"),

     install_requires = ['netaddr', 'mako', 'networkx>=1.5', 
         'nose',
         'pexpect', 'beaker',],

     classifiers = [
         "Programming Language :: Python",
         "Development Status :: 3 - Alpha",
         "Intended Audience :: Science/Research",
         "Intended Audience :: System Administrators",
         "Intended Audience :: Telecommunications Industry",
         "License :: Other/Proprietary License",
         "Operating System :: MacOS :: MacOS X",
         "Operating System :: POSIX :: Linux",
         "Topic :: System :: Networking",
         "Topic :: System :: Software Distribution",
         "Topic :: Scientific/Engineering :: Mathematics",
         ],     
 
)
