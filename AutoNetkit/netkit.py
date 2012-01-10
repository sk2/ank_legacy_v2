"""
Netkit common functions   
"""
__author__ = """\n""".join(['Simon Knight (simon.knight@adelaide.edu.au)',
                            'Hung Nguyen (hung.nguyen@adelaide.edu.au)'])
#    Copyright (C) 2009-2010 by 
#    Simon Knight  <simon.knight@adelaide.edu.au>
#    Hung Nguyen  <hung.nguyen@adelaide.edu.au>
#    All rights reserved.
#    BSD license.
#

# SSH connection code based on
# linux.byexamples.com/archives/346/python-how-to-access-ssh-with-pexpect/
import config
import logging
LOG = logging.getLogger("ANK")

try:
    import pexpect
    import pxssh
except:
    LOG.error("Netkit deployment requires pexpect")
    raise

import os  
import sys


from netaddr import IPNetwork



#based on http://bytes.com/topic/python/answers/619040-using-pxssh


#NOTE: only tested with assumption that SSH keys have been setup 

#NOTE assumes taplist.csv exists in the LAB directory

# Prompt Netkit uses, used for expect
NETKIT_PROMPT = "~#"   
   
#.............................................................................
class Netkit:      
    """Common functions for interacting with a Netkit server."""
    

    def __init__(self, host=None, username=None, shell_type="bash", 
                 tapsn=IPNetwork("172.16.0.0/16")):
        self.host = host
        self.username = username
        self.shell = None         
        self.shell_type = shell_type 

        # Assume that the admin 
        self.tap_host = tapsn[1]
        self.tap_ip = tapsn[2]
        self.NETKIT_PROMPT = NETKIT_PROMPT
             
        #TODO configure these
        self.tap_hostname = "taptunnelvm"

        self.local_server = True
        if self.host and self.username:
            # Host and Username set, so ssh will be used
            #TODO: make sure these are confirmed by the connect_server function
            self.local_server = False
        
        #TODO: state machine maintained by the connecting functions
        # Disconnected | Netkit | TapHost 
        
        # use normal logger for logging? can we do this with pxssh?? 
        self.logfile = open( os.path.join(config.log_dir, "pxssh.log"), 'w')
           
    def get_shell(self):   
        """ Returns a shell connection to the Netkit server.
            Connects server if no current connection.
            Handles both remote (via SSH) and local server connections."""
        if self.shell:             
            # Already connected
            return self.shell
        else:           
            # Need to connect first
            self.connect_to_server()
            return self.shell
    
    def transfer_file(self, local_file):
        """Transfers file to remote host using SCP"""
        # Sanity check
        if self.local_server:
            LOG.warn("Can only SCP to remote Netkit server")
            return

        child = pexpect.spawn("scp {0} {1}@{2}:.".format(local_file,
            self.username, self.host))      
        child.logfile = self.logfile

        child.expect(pexpect.EOF) 
        LOG.debug(  "SCP result %s"% child.before.strip())
        return 
        
    def connect_to_server(self):  
        """Connects to Netkit server (if remote)"""   
        
        #TODO: make internal (private) function
        
        #TODO: check state is disconnected
        
        # Connects to the Linux machine running the Netkit lab   
        shell = None     
        if self.host and self.username:  
            # Connect to remote machine

            ssh_link = self.shell
            if ssh_link != None: 
                # ssh_link already set
                return ssh_link

            shell = pxssh.pxssh()    
            shell.logfile = self.logfile
            LOG.info(  "Connecting to {0}".format(self.host) ) 

            shell.login(self.host, self.username)
            # with pass: shell.login(self.host, self.username, self.password)

            LOG.info(  "Connected to " + self.host )  
            #TODO: set state to Netkit
        else:   
            shell = pexpect.spawn (self.shell_type) 
            shell.sendline("uname")
            
            shell.logfile = self.logfile    
            shell.setecho(True)  
            # Check Linux machine (Netkit won't run on other Unixes)   
            i = shell.expect(["Linux", "Darwin", pexpect.EOF, NETKIT_PROMPT]) 
            if i == 0:
                # Machine is running Linux. Send test command (ignore result)
                shell.sendline("ls") 
            elif i == 1:
                LOG.warn("Specified Netkit host is running Mac OS X, "
                    "please specify a Linux Netkit host.")
                return None 
            else:
                LOG.warn("Provided Netkit host is not running Linux")

        self.shell = shell   
        return


    def check_nk_installed(self):  
        """Checks that Netkit is installed for given user"""
        
        LOG.debug("Checking Netkit installed")
       
        #Check length of netkit env var is nonzero
        shell = self.shell
        chk_cmd = 'hash lstart 2>&- && echo "Present" || echo >&2 "Absent"\n'
        shell.sendline(chk_cmd)
        i = shell.expect (["Present", "Absent"])    
        if i == 0:        
            LOG.debug("Netkit env var present")
            # Netkit env var present, assume nk installed
            return True
        else:
            LOG.debug("Netkit env not var present")
            return False

    
    def check_tunnel(self):  
        """Checks TAP tunnel is active"""
        
        LOG.debug("Checking tunnel")
        tap_hostname =  self.tap_hostname 
        shell = self.shell               
                                
        taphost_started = False
        #TODO: check can ping tap dest also

        shell.sendline("vlist\n")    
        
        # Limit max lines to 1000
        for dummy in range (0, 1000):
            i = shell.expect ([
                "\w+\s+(" + tap_hostname + ")\s+\d+\s+\d+", # Match host
                pexpect.EOF,
                "Total virtual machines", # Last line of vlist output
                "vlist: not found",
                ])
            if i == 0:  
                taphost_started = True    
                break
            if i == 3:
                LOG.warn("Unable to find vlist command")
            else:     
                # Reached end
                # TODO: look at using this instead of infinite loop
                # Throw exception if reached here      
                break                                    
        
        # See if Tap host running  
        if taphost_started:
            LOG.debug("Tap host machine active, tunnel should be up")
            #todo: ping tap host machine ie tap_host ip to check is active   
            return True                                                       
        else:
            LOG.info("Starting tap tunnel: please enter sudo password and type '^]' (Control and right square bracket)"
                    "to return to AutoNetkit")
            shell.sendline("vstart %s --con0=none --eth0=tap,%s,%s" % ( self.tap_hostname, self.tap_host, self.tap_ip))
            sys.stdout.write (shell.after)
            sys.stdout.flush()
            shell.interact()
# Sendline in case user didn't have to sudo, and so didn't do anything
            shell.sendline()

            return True
        
    def disconnect_vm(self, shell): 
        """ Disconnects from a Netkit virtual machine"""
        shell.sendline("exit")
        shell.expect("Connection to \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3} closed.")
        return

    def connect_vm(self, host, shell, username="root", password="1234"): 
        """ Connects to a Netkit virtual machine"""
#TODO: modify this to use own shell, to allow multithreading
                              
        shell = self.get_shell()
        #TODO: maintain state - eg if connected to netkit server or to
        # a tap host
        
        #Used within a connection already established
        #TODO fix handling if ssh to remote machine first (eg from mac),
        #  or already on host machine (eg on linux running netkit)   
        
        #Connects using ssh, handling the different cases 
        #based on 
        #linux.byexamples.com/archives/346/python-how-to-access-ssh-with-pexpect
        LOG.debug( "Connecting to tap host {0}".format(host) )
        
        ssh_newkey = 'Are you sure you want to continue connecting'
        # my ssh command line      
        shell.sendline('ssh {0}@{1}'.format(username, host) )
       
        i = shell.expect([ssh_newkey, 'password:', pexpect.EOF, NETKIT_PROMPT]) 
        if i == 0:
            LOG.debug("Accepting new SSH key")
            shell.sendline('yes')
            i = shell.expect([ssh_newkey, 'password:', pexpect.EOF])
        if i == 1:
            LOG.debug( "Giving password")
            shell.sendline(password)
            shell.expect(NETKIT_PROMPT)
        elif i == 2:
            LOG.debug( "Either got key or connection timed out")
        elif i == 3:   
            LOG.debug( "Connected using authentication key")
        
        LOG.debug("Connected to {0}".format(host)  )
        
        return
    
           
