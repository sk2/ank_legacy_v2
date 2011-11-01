Installation
============        
         
Overview
-------------
Use easy_install::
                                
	easy_install AutoNetkit

Depending on your operating system setup, you may need to install using sudo::

	sudo easy_install AutoNetkit
                            
Detailed instructions thanks to Joel Obstfeld
      
Windows Installation
--------------------- 

Download Python for windows from:

	http://www.python.org/ftp/python/2.7.2/python-2.7.2.msi

Install the package

Download easy_install for windows

	http://pypi.python.org/packages/2.7/s/setuptools/setuptools-0.6c11.win32-py2.7.exe#md5=57e1e64f6b7c7f1d2eddfc9746bbaf20

Install the package

Start a command window (run cmd.exe) and cd to directory to which Python was installed (defaults to c:\Python27)

cd into the Scripts directory.

Install the PIP package management tool by typing

	easy_install pip

Once complete, install AutoNetkit as follows:

	pip install AutoNetkit

AutoNetkit is now installed in the 'scripts' directory


Mac Installation
-----------------       
Mac OS X 10.6 includes Python 2.6.1 which is sufficient to run Autonetkit

Download:

	http://pypi.python.org/packages/2.6/s/setuptools/setuptools-0.6c11-py2.6.egg#md5=bfa92100bd772d5a213eedd356d64086

Place in a directory then

	sudo sh ./setuptools-0.6c11-py2.6.egg 

then install pip package management tools

	sudo easy_install pip

then install package library

	sudo pip install AutoNetkit          
	      
Updating AutoNetkit
-------------------
to perform an update of the AutoNetKit tool, 

WINDOWS:

open a cmd session (run cmd.exe) cd into the scripts directory where Python has been installed (c:\Python27\Scripts), then

pip install --upgrade AutoNetkit

MAC:

sudo pip install --upgrade AutoNetkit        
