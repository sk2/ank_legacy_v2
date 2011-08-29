"""
Netkit deployment   
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

#TODO: move into plugins


import pexpect
import ank_pxssh   
import os  
import re    
import csv    
import random   
import time      

import config
LOGGER = config.logger    

import logging
LOG = logging.getLogger("ANK")

import autonetkit as ank
import networkx as nx

from netaddr import IPNetwork

#TODO: remove these   
import pprint        
pp = pprint.PrettyPrinter(indent=4)       

#import getpass


#based on http://bytes.com/topic/python/answers/619040-using-pxssh


#NOTE: only tested with assumption that SSH keys have been setup 

#NOTE assumes taplist.csv exists in the LAB directory

# Prompt Netkit uses, used for expect
NETKIT_PROMPT = "~#"   
   
#.............................................................................
class NetkitDeploy:      
    """Deploys AutoNetkit lab to Netkit server."""
    

    def __init__(self, host=None, username=None, 
                 tap_subnet=IPNetwork("172.16.0.0/16")):
        self.host = host
        self.username = username
        #TODO: remove password  
        self.password = None
        self.shell = None          
             
        #TODO configure these
        # Tap host assumed to be the first two IPs
        # TODO: allow user to specify tap host also

        self.tap_host = "172.16.0.1"
        self.tap_dest = "172.16.0.2"   
        self.tap_hostname = "taptunnelvm"
                      
        #TODO: see if this is needed
        self.prompt = None   
                    
        self.local_nk = True
        if self.host and self.username:
            #NK host is on same machine as ANK
            self.local_nk = False
        else:                    
            # NK host is on another machine to ANK
            self.local_nk = True
        
                                           
        self.loopback_list = {}
        self.loopback_list_forward = {}     
        self.interface_list = {} 
        self.tap_list = {} 
        

        # easy reference              
        #TODO: clean this up - ie remove
        self.remote_nk = not self.local_nk

        self.logfile = open( os.path.join(config.log_dir, "pxssh.log"), 'w')
           
    def load_data(self, netkit_dir):   
        #TODO: find better way to pass around taplist, interfacelist, etc than
        #using text file: possibly use global reference file
        # (similar to settings?)
        #try and load the taplist  
        #TODO add exception throwing if can't read taplist
        f_taplist = open(netkit_dir+"/taplist.csv", 'r') 
        try:
            reader = csv.reader(f_taplist)
            for host, address in reader:
                self.tap_list[host] = address
        finally:
            f_taplist.close()      

        #TODO add exception throwing if can't read 
        f_loopbacklist = open(netkit_dir+"/identifyingLoopback.csv", 'r') 
        # Note format is [address] = host, not [host] = address, ie does reverse
        # DNS style lookups
        try:
            reader = csv.reader(f_loopbacklist)   
            for host, address in reader:
                #TODO: may have reverse key conflicts if same loopback assigned
                # to multiple hosts in same lab, but for different ASs
                self.loopback_list[address] = host     
                self.loopback_list_forward[host] = address      
        finally:
            f_loopbacklist.close()                
        #TODO add exception throwing if can't read 
        f_interfacelist = open(netkit_dir+"/interfaceList.csv", 'r') 
        # Note format is [address] = host, not [host] = address
        # ie does reverse DNS style lookups
        try:                      
            reader = csv.reader(f_interfacelist)
            for host, address in reader:    
                self.interface_list[address] = host        
        finally:
            f_interfacelist.close()     
    
    
    def stop_lab(self, netkit_dir):  
        """Halts running Netkit lab"""
        
        LOGGER.info(  "Halting previous lab" )
        shell = self.shell      
        
        # See if lab folder exists (or if fresh installation)       
        # check for remote directory
        if self.remote_nk:
            # only applicable for remote (ie copied over) labs
            shell.sendline("[ -d " + netkit_dir + 
                " ] && echo 'Present' || echo 'Absent'\n")
            shell.prompt() 
            result = shell.before 
            # Examine result line by line 
            # (as command itself is also often echoed back)  
            for line in result.splitlines():
                if line == "Absent":
                    # Folder doesn't exist => no Lab to stop      
                    LOGGER.debug("Lab directory doesn't exist, no lab to stop") 
                    shell.sendline()
                    shell.prompt() 
                    return    
                
        
        #stop lab     
        shell.sendline("cd " + netkit_dir)
        
        #TODO: also halt any machine listed in this lab, eg after the
        # lhalt -q if any hosts in the new lab are still
        # running then vhalt -q them
        
        # Use -q flag to shutdown hosts quickly     
        
        shell.sendline("lhalt -q")
        #need longer timeout as this may take a while  
        #TODO base the timeout on the number of machines,
        #  say 10 seconds per machine  
        # Halting "AS1r1"...
        pattern = "Halting \"(\w+)\"..."   
        finished = "Lab has been halted."
        # Limit max lines to 1000
        for dummy in range (0, 1000):
            i = shell.expect ([pattern, finished, pexpect.EOF])
            if i == 0:
                LOGGER.debug(  "Halted host " + shell.match.group(1)    )  
            elif i == 1: 
                LOGGER.debug(  "Finished halting lab"    ) 
                break
            else:    
                break # reached end
        return
    
    def deploy(self, netkit_dir):  
        # stops lab, copies new lab over, starts lab  
        shell = self.connect_nk_server()  
        
        if not shell:
            # Problem has occured, end deployment
            LOGGER.warn("Unable to connect to Netkit host. Ending deployment.")
            return  
        
        nk_inst = self.check_nk_installed() 
        if not nk_inst:
            LOGGER.warn("Netkit environment variable not found. \
                Please check Netkit is correctly installed.")
            return 
        else:
            LOGGER.debug("Netkit environment variable found, proceeding")
                                         
        tunnel_active = self.check_tunnel()  
        if not tunnel_active:
            LOGGER.warn("Netkit TAP tunnel not setup. \
                Please manually configure.")
            return 
        else:                 
            LOGGER.debug("Netkit TAP tunnel present, proceeding")
        
        #TODO: reinstate this step once templates are filled in
        #self.load_data(netkit_dir)
        self.stop_lab(netkit_dir)
        self.copy_and_start_lab(netkit_dir)
        
    
    def get_password(self):     
        #TODO: replace with direct self.password access
        return self.password

 
    def connect_nk_server(self):  
        """Connects to Netkit server (if remote)"""
        
        # Connects to the Linux machine running the Netkit lab   
        shell = None     
        if self.host and self.username:  
            # Connect to remote machine

            ssh_link = self.shell
            if ssh_link != None: 
                # ssh_link already set
                return ssh_link

            #TODO: check if replace with function call here
            shell = ank_pxssh.pxssh()    
            shell.logfile = self.logfile
            self.prompt = shell.PROMPT    

            LOGGER.info(  "Connecting to {0}".format(self.host) ) 
            if self.get_password() == None:
                # Try logging in with ssh key
                shell.login(self.host, self.username)
            else:            
                # Try logging in with password        
                shell.login(self.host, self.username, self.password)

            LOGGER.info(  "Connected to " + self.host )
        else:   
            shell = pexpect.spawn ('sh') 
            shell.sendline("uname")
            
            #shell.logfile = self.logfile  
            shell.logfile = self.logfile    
            shell.setecho(True)  
            #check linux machine   
            
            #TODO: see if prompt is needed
            self.prompt = "$"

            i = shell.expect(["Linux", "Darwin", pexpect.EOF, NETKIT_PROMPT]) 
            if i == 0:
                # Linux, this is fine, continue on 
                shell.sendline("ls") 
            elif i == 1:
                LOGGER.warn("Specified Netkit host is running Mac OS X.\
                    Please specify a Linux Netkit host.")
                return None

    #TODO: checl this is required
        self.shell = shell   
        return shell


    def check_nk_installed(self):  
        """Checks that Netkit is installed for given user"""
        
        LOGGER.debug("Checking Netkit installed")
       
        #Check length of netkit env var is nonzero
        shell = self.shell
        shell.sendline("[ -n \"${NETKIT_HOME}\" ] \
            && echo 'Present' || echo 'Absent'")
        i = shell.expect (["Present", "Absent"])    
        if i == 0:         
            # Netkit env var present, assume nk installed
            return True
        else:
            return False

    
    def check_tunnel(self):  
        """Checks TAP tunnel is active"""
        
        LOGGER.debug("Checking tunnel")
        # Tries to setup the ssh tunnel   
        #TODO: make this scale to the tap address
        # (needs to pull from the internetwork object)
             
        tap_hostname =  self.tap_hostname 
        shell = self.shell               
                                
        taphost_started = False
        #TODO: check can ping tap dest also

        shell.sendline("vlist\n")    
        
        #  sknight          taptunnelvm        1471      41632   
        #TODO: sub in taphost
        pattern = "\w+\s+(" + tap_hostname + ")\s+\d+\s+\d+"     
        # The last line of vlist output
        last_line = "Total virtual machines"
        # Limit max lines to 1000
        for dummy in range (0, 1000):
            i = shell.expect ([pattern, pexpect.EOF, last_line])
            if i == 0:  
                taphost_started = True    
                break
            else:     
                print "reached end"      
                break # reached end                                     

        
        # See whether the machine was found to be active or not
        if taphost_started:
            LOGGER.debug("Tap host machine found to be active, \
                tunnel should be up")
            #todo: ping tap host machine ie tap_host ip to check is active   
            return True                                                       
        else:
            LOGGER.warn("Please setup tap network link manually")
            LOGGER.warn("eg vstart {0} --con0=none --eth0=tap,\
                        {1},{2}".format( self.tap_hostname, self.tap_host,
                                        self.tap_dest))
               
             
            return False
        
    def copy_and_start_lab(self, netkit_dir):   
        """Starts Netkit lab. If Netkit host is remote,\
            will also copy across lab."""        
        
        #TODO: split copy out so two seperate functions
        
        LOGGER.info(  "Copying and starting new lab" )
        
        shell = self.shell  
                                      
        if self.remote_nk:    
            # Copy over and extract lab on remote machine
            
            LOGGER.info("Copying Lab over")    
                                                
            # Strip any trailing slashes in definition of lab dir  
            #TODO: use proper system function for this not cmd
            tar_file = "netkit_lab.tar.gz"   
            cmd = "tar -czf " + tar_file + " " + netkit_dir      
            os.system(cmd)       
            LOGGER.debug( "Archived Lab")
        
            # and scp over
            child = pexpect.spawn("scp {0} {1}@{2}:.".format(tar_file,
                self.username, self.host))      
            child.logfile = self.logfile
                                                               
            #TODO: clean this up to be more automatic (with expect)
            if (self.get_password() != None):   
                # password has been provided, send it when prompted
                child.expect('.ssword:*')
                child.sendline(self.password)
         
            child.expect(pexpect.EOF) 
            LOGGER.debug(  "SCP result {0}".format(child.before) ) 
  
        
            LOGGER.debug(  "Connected to host {0}".format(self.host))
        
            shell.sendline("cd ")
            shell.prompt() 

            # remove lab directory
            shell.sendline("rm -rf  " + netkit_dir + "/*")
            shell.prompt() 
            LOGGER.debug(  "Removed previous lab directory" )

            shell.sendline("tar -xzf  " + tar_file)
            shell.prompt() 
            LOGGER.debug(  "Extracted new lab"  )
            #cd   
            
        shell.sendline("cd " + netkit_dir)
        
        #get number of machines in lab
        shell.sendline("linfo")
        machine_count = 0   
        machine_list = []
        #  sknight          taptunnelvm        1471      41632  
        pattern = "The lab is made up of (\d+) virtual machines \( ((?:\w+ ?)+\w+)\)"  
        # Limit max lines to 1000
        for dummy in range (0, 1000):
            i = shell.expect ([pattern, pexpect.EOF])
            if i == 0:
                machine_count = shell.match.group(1)
                machine_list = shell.match.group(2)
                machine_list = machine_list.split()
                LOGGER.debug("hosts in lab are: " + ", ".join(machine_list) )  
                break
            else:    
                break # reached end

       
        # Check virtual machines have been halted 
        # TODO break this into a seperate function, for clarity  
        LOGGER.info("Checking all previous machines shutdown")   
        
        
        #  sknight          taptunnelvm        1471      41632  
        pattern = "\w+\s+(\w+)\s+\d+\s+\d+"    
        # The last line of vlist output
        last_line = "\nTotal virtual machines"
        
        
        # Limit max lines to 1000    
        can_proceed = True
        while 1:
            can_proceed = True
            shell.sendline("vlist ")
            for dummy in range (0, 1000):  
                
                i = shell.expect ([pattern, pexpect.EOF, last_line])   
                if i == 0:
                    vhost = shell.match.group(1)  
                    if vhost in machine_list:            
                        LOGGER.debug( "Machine " + vhost + 
                            " is in list of machines that should be shutdown" )
                        can_proceed = False
                        # send this machine command to halt - in event 
                        #was not present in lab folder but present
                        # from previous run
                        shell.sendline("vhalt -q {0}".format(vhost))  
                else: 
                    # Finished looking at active hosts     
                    break
                         
            # reached end, see if allowed to proceed - if not then retry    
            if(can_proceed):   
                # Break out of infinite loop, lab machines are shutdown
                break
            else:
                # Some machines still running, delay
                delay = 5        
                LOGGER.info("Some hosts still running, retrying in \
                    {0} seconds".format(delay))
                time.sleep(delay)  
                                          
        
        LOGGER.debug("All required hosts shutdown, proceeding")
                                                  
        #start lab   
        LOGGER.info( "All previous machines shutdown, starting lab")
        # Start 5 machines at once (-p 5)    
        # Don't try to start console (con0 = none)
        shell.sendline("lstart -p5 -o --con0=none")
        
        starting_host_pattern = 'Starting "(\w+)"...'
        completed_pattern = "The lab has been started."  
        still_running_pattern = 'vstart: Virtual machine "(\w+)" is \
            already running. Please'   
        terminated_pattern = "Terminated"      
        tunnel_error = "Error while configuring the tunnel."
        current_machine_index = 1             
        
        # Start infinite loop, as don't know how many lines to expect.
        # Leave when receive correct outpu
        while 1:      
            i = shell.expect([completed_pattern, starting_host_pattern,
                still_running_pattern, pexpect.TIMEOUT, pexpect.EOF,
                terminated_pattern, tunnel_error])   
            
            if i == 0:     
                # Finished starting lab 
                status =  "Finished starting Lab, \
                    {0} machines started".format(machine_count) 
                LOGGER.info(  status  )  
                # Leave infinite loop
                break                                                    
                
            elif i == 1:                  
                status = "Starting {0} ({1}/{2})".format( 
                    shell.match.group(1), current_machine_index, machine_count)
                LOGGER.info(  status  )  
                current_machine_index += 1    
            elif i == 2:
                # Shouldn't reach here if all hosts correctly shutdown
                vhost = shell.match.group(1)
                LOGGER.warn("Error starting lab, machine {0}\
                    is still running".format(vhost))
            elif i == 3:
                LOGGER.debug( "timeout"  ) 
            elif i == 4:
                LOGGER.debug( "EOF" )
            elif i == 5:    
                LOGGER.warn("An error has occurred, startup terminated.")   
                return   
            elif i == 6:                                                        
                #TODO integrate this with the setup tap tunnel function   
                pass
                #TODO: work ouyt why reaching here
                #LOGGER.warn("An error has occurred: {0}. Ensure tunnel is
                # setup before starting lab".format(tunnel_error))
                #LOGGER.warn("eg vstart {0} --con0=none 
                #  --eth0=tap,{1},{2}".format( 
                # self.tap_hostname, self.tap_host, self.tap_dest))
                # Stop trying to start lab
                #break
                    
                       
                
        #TODO check all machines are running, similar to checking they 
        # were shutdown. Can then do fast (ie no checking) startup
        
        return
    
    def getMemInfo(self):     
        #Scrapes /proc/meminfo for free memory, returns result in kB

        LOGGER.info("Querying memory information")    

        shell = self.shell   

        LOGGER.debug(  "Connected to host {1}".format(self.host)) 

        #stop lab     
        shell.sendline("cat /proc/meminfo") 
        memtotal_pattern = "MemTotal:\W+(\d+) kB"  
        
       
        while 1:      
            i = shell.expect([memtotal_pattern,
                              pexpect.TIMEOUT, pexpect.EOF])   
                
            #TODO: handle other cases of timeout, prompt, etc
            # (better error handling)   
            if i == 0:   
                # Got memtotal  
                freeMem =  shell.match.group(1)
                # convert to Mb  
                freeMem = int(freeMem)/1024 
                return freeMem
       
        return
                    
    def tailBGPLog(self, host):
        # Tails the bgp log of the host provided          
        #connect to host              
        ssh_link = self.connect_nk_server() 
        
        tap_ip = self.resolvehost_to_tap_ip(host) 
        LOGGER.info("tailing BGP log of {1} at {2}".format(host, tap_ip))
        
        self.connect_taphost(ssh_link, tap_ip) 
        
        log_date_pattern = "\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}" 
        no_such_file_pattern = "No such file or directory"
        
        # First read the file to date, then tail new entries 
        log_file = "/var/log/zebra/bgpd.log"
        ssh_link.sendline("cat " + log_file)    
        while 1:      
            i = ssh_link.expect([log_date_pattern, NETKIT_PROMPT,
                                 no_such_file_pattern])   
            if i == 0:                
                # Suppress newline using comma as
                #  newline alreadyy in captured output
                print ssh_link.after + " " + ssh_link.before,    
            elif i == 1:
                # Finished reading existing file, tail new entries
                break
            elif i == 2:
                LOGGER.warn("Unable to tail BGP log file: {1}\
                            file does not exist".format(log_file) )
        return
                        
                   
        
        ssh_link.sendline("tail -f /var/log/zebra/bgpd.log")    
        while 1:      
            i = ssh_link.expect([log_date_pattern])   
            if i == 0:                
                # Suppress newline using comma as newline
                # already in captured output
                print ssh_link.after + " " + ssh_link.before,                
        return
    

    def verify(self, graph):
        ssh_link = self.connect_nk_server()

        rev_dns = {}

        for s, t, data in graph.edges(data=True):
            # Format of 192.168.0.1: AS1rA
            int_ip = data['ip']
            # Convert from IP object to string for easy comparison
            int_ip = str(int_ip)
            rev_dns[int_ip] = s
        
        for my_as in ank.get_as_graphs(graph): 

            success_count = 0
            fail_count = 0

            apsf = nx.all_pairs_dijkstra_path(my_as)
            for src, data in apsf.items():    
                tap_ip = src.tap_ip
                self.connect_taphost(ssh_link, tap_ip)

                uptime = self.get_tap_machine_uptime(ssh_link)      
                LOGGER.debug("Uptime of {0} is {1} ".format(src, uptime) )
                if(float(uptime) < 60):
                    LOGGER.warn("host {0} uptime is only {1} seconds. Routes\
                        may not have fully converged".format(src, uptime))

                LOGGER.info("Tracing routes for {0}".format(src))
                for dest, path in data.items():           

                    if src == dest:
                        # Skip path to self (as not useful)
                        continue
                
                    # Store path for this source-destination pair
                    #parsed_path = []
                    #for hop in raw_path:
                    #    parsed_path.append(hop.full_name) 
                    #    #add to the list
                    #    parsed_pathlist.append(parsed_path) 

                    expected_path = path

                    dest_ip = dest.lo_ip.ip

                    # Append destination to expected_path to match
                    #  output of traceroute
                    actual_path = self.traceroute(ssh_link, dest_ip)    
                    # Add source to start of paths, easier to read
                    #expected_path.insert(0,source) 
                    #actual_path.insert(0,src)

                    # convert actual path to hostnames
                    actual_resolved = [rev_dns[host] for host in actual_path if
                                       host in rev_dns]
       
                    # append start and dest to meet format of tracert
                    actual_resolved.insert(0, src)
                    actual_resolved.append(dest)

                    # Check if they match     
                    if expected_path == actual_resolved:
                        success_count += 1 
                    else:
                        LOGGER.debug("Different paths found. \
                            Checking path lengths")

                        # See what path cost is (from routing tables)
                        #cost = self.getPathCost(ssh_link, dest)  
                        #TODO: analyse if equal cost path
                        # Note no netx fn to work out both path and distance, so
                        # only calculate distance when required
                        expected_distance = nx.dijkstra_path_length(my_as, src,
                                                                    dest)

                        # Convert expected path into link pairs
                        expected_path_pairs = [ (path[i-1], path[i]) for 
                            i in range(1, len(path))]
                        # now convert to router objects
                        actual_distance = sum( my_as[a][b]['weight'] for a, b in
                                              expected_path_pairs)
                 
                        if expected_distance == actual_distance:
                            # We have an equal cost route, this is fine
                            success_count += 1
                            LOGGER.debug("Actual path has same cost as \
                                expected shortest path")
                        else:
                            # We have taken a different path, with a different
                            # cost. This is bad!
                            fail_count += 1
                            LOGGER.debug("Error. Expected {0} with cost {1},\
                                got {2} with cost {3}".format(
                                expected_path, expected_distance,
                                actual_resolved, actual_distance) )
                self.disconnect_taphost(ssh_link)
                LOGGER.info("{0}/{1} correct".format(success_count,
                    (success_count + fail_count)))
            LOGGER.info("Total: {0}/{1} correct".format(success_count,
                (success_count + fail_count)))
    
            return

    def get_tap_machine_uptime(self, shell):
        # Returns, in seconds, the uptime of the current machine
          
        shell.sendline("cat /proc/uptime")
        shell.expect(NETKIT_PROMPT) 
        line = shell.before  
        m = re.search("(\d+.\d+) \d+.\d+", line)      
        if  m: 
            return str(m.group(1))  
        
               

        
    
    def resolve_ip(self, ip_addr):
        #TODO: need to look up ip from graph's interface list...
        # need to generate that from a list comp on graph once moved over

        return ip_addr
        return str(self.interface_list.get(ip_addr))  
    
    def resolvehost_to_tap_ip(self, host):
        return self.tap_list[host]
            
    def get_random_int_ip(self):
        #returns a random interface IP, used for traceroute and ping etc
        return random.choice(self.interface_list.keys())   
        
    def ping(self, shell, destination):  
        shell.sendline("ping {0} -c 1".format(destination))
        #TODO - extract ping results
    
    def getPathCost(self, shell, destination):   
        """ Extracts metric from kernel routing table """

        # look up routing tables 
        shell.sendline("route -n ")     
        cost = -1
        
        ip_pattern = "(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})\W+\d{1,3}.\
            \d{1,3}.\d{1,3}.\d{1,3}\W+\d{1,3}.\
            \d{1,3}.\d{1,3}.\d{1,3} +\w\w+\W+(\d+)"
        while 1:      
            i = shell.expect([ip_pattern, NETKIT_PROMPT,
                pexpect.TIMEOUT, pexpect.EOF]) 
                
            if i == 0:
                # See if matches required destination
                if shell.match.group(1) == destination: 
                    # This is the row for the required destination
                    # get the cost
                    cost = shell.match.group(2)    
                    # continue until end of input
            elif i == 1:    
                # Prompt, end of data
                break
        return cost           
        
        
        
    def traceroute(self, shell, destination, probe_count=1,
        wait_time = 0.3, max_probe_count=5, max_wait_time=1):        
        # probe_count number of probes to send (default usually 3)  , 
        # and max (incremented on timeout)   
        # wait_time seconds per probe (default usually 5), 
        # and max (incremented on timeout)      
        path = []
        
        #TODO: refactor this duplicated code
        # Some magic: If destination is not an IP address, attempt to resolve
        #m = re.search("\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}", destination)      
        #if not m:
        #    # Not an IP address, attempt to resolve  
        #    LOGGER.debug("Destination {0} not an IP address, attempting
        # to resolve hostname".format(destination))
        #    destination = self.resolvehostToInterfaceIP(destination)
        #    LOGGER.debug("Resolved to {0}".format(destination)) 
        #    #TODO: if not able to resolve, log an error and return
        # rather than try to trace
        
        LOGGER.debug( "Tracing route to {0}".format(destination)) 
        
        shell.sendline("traceroute -q {0} -w {1} {2}".format(probe_count,
            wait_time, destination) ) 
        
        unreachable_pattern = "sendto: Network is unreachable" 
        ip_pattern = "\d+  (?:\*? ?)+(\d{1,3}.\d{1,3}.\d{1,3}.\
            \d{1,3}) +\(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}\)  (\d+) ms"
        dns_pattern = "\d+  (?:\*? ?)+[a-z]{2,3}\d.(\w+).\
            \w+ +\(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}\)  (\d+) ms" 
        # Timeout for traceroute occurs when receive an asterisk for each probe
        traceroute_timeout_pattern = "\d+  " + "\*\W"*probe_count        
        
        # Start infinite loop, as don't know how many lines to expect.
        # Leave when receive correct output
        
        while 1:      
            i = shell.expect([unreachable_pattern, ip_pattern, dns_pattern,
                NETKIT_PROMPT, pexpect.TIMEOUT, pexpect.EOF,
                traceroute_timeout_pattern])   
            
            if i == 0:     
                # Destination network is unreachable 
                # Stop the rest of the trace  
                LOGGER.debug( "Network unreachable, killing traceroute")
                # Send terminate command
                shell.sendintr()
                path.append("Unreachable")
                break
            elif i == 1:
                # ip pattern                  
                #TODO check delay confirms that it was an integer value,
                # ie not a timeout (ms should do this?)
                LOGGER.debug( "Reply from host {0} delay of {1}".format(
                    shell.match.group(1), shell.match.group(2)  ) )
                # Convert interface IP into hostname
                host =  self.resolve_ip(shell.match.group(1)) 
                # Store path entry
                path.append(host)      
            elif i == 2:
                # dns pattern   
                LOGGER.debug( "Reply from host {0} delay of {1}".format(
                    shell.match.group(1), shell.match.group(2)  ) )
                host = shell.match.group(1)
                path.append(host)   
            elif i == 3:
                # netkit prompt, finished tracing
                break 
                     
            elif i == 4:
                LOGGER.debug( "timeout"  ) 
            elif i == 5:
                LOGGER.debug( "EOF" )   
            elif i == 6: 
                # Kill the traceroute   
                shell.sendintr()
                shell.expect(NETKIT_PROMPT)  
                # Increment the wait time and probe count 
                probe_count = probe_count + 1
                wait_time = wait_time + 0.2         
                                          
                # Check if this exceeds max  
                if(probe_count > max_probe_count) or (wait_time > max_wait_time):
                    # Give up, as exceeded max
                    path.append("Unreachable")  
                    break   
                else:
                    # Initiate new traceroute, continue on 
                    # reset the path  
                    LOGGER.debug("Timeout, restarting traceroute with\
                        {0} probes and {1} wait time".format(probe_count,
                        wait_time)  )
                    path = []   
                    shell.sendline("traceroute -q {0} -w {1} {2}".format(
                        probe_count, wait_time, destination) ) 
                    # Handle case of command being echoed back
                    # TODO: need more elegant solution to this logic  
                    shell.expect([NETKIT_PROMPT, "traceroute"])
                
                
        
        # check no more processes running, catches stray runaway traceroutes
        #(TODO: make the handling of runaway traceroutes cleaner,
        # and handle in above loop)
        # Send terminate command
        shell.sendintr()
        # Expect netkit prompt after terminating any processes
        shell.expect(NETKIT_PROMPT)  
        
        return path 
    

                                             
                                             

    def disconnect_taphost(self, shell):
        shell.sendline("exit")
        shell.expect("Connection to \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3} closed.")
        return

    def connect_taphost(self, shell, host, username="root", password="1234"):
        #Used within a connection already established
        #TODO fix handling if ssh to remote machine first (eg from mac),
        #  or already on host machine (eg on linux running netkit)   
        
        #Connects to ssh, handling the different cases 
        #based on 
        #linux.byexamples.com/archives/346/python-how-to-access-ssh-with-pexpect
        LOGGER.debug( "Connecting to tap host {0}".format(host) )
        
        ssh_newkey = 'Are you sure you want to continue connecting'
        # my ssh command line      
        shell.sendline('ssh {0}@{1}'.format(username, host) )
       

        i = shell.expect([ssh_newkey, 'password:', pexpect.EOF, NETKIT_PROMPT]) 
        if i == 0:
            LOGGER.debug("Accepting new SSH key")
            shell.sendline('yes')
            i=shell.expect([ssh_newkey, 'password:', pexpect.EOF])
        if i == 1:
            LOGGER.debug( "Giving password")
            shell.sendline(password)
            shell.expect(NETKIT_PROMPT)
        elif i == 2:
            LOGGER.debug( "Either got key or connection timed out")
        elif i == 3:   
            LOGGER.debug( "Connected using authentication key")
        
        LOGGER.debug("Connected to {0}".format(host)  )
        
        return
    
  
        
    def parse_snmp_bgp_table(self, host):
        #BGP4-MIB::bgp4PathAttrBest.(\d+.\d+.\d+.\d+).(\d+).(\d+.\d+.\d+.\d+) 
        # = INTEGER: (\w+)
        # Tails the bgp log of the host provided          
        #connect to host                
        ssh_link = self.connect_nk_server()       
        
        tap_ip = self.resolvehost_to_tap_ip(host)       
        #TODO: remove
        LOGGER.info("SNMP query BGP table of {0} at {1}".format(host, tap_ip)) 
        
        bgp_data = {}
        
        #TODO: get each of these as individual dictionaries returned, 
        # and then split/zip/merge them into main dictionary (much more
        # concise code then)
        # get prefixes first
                                       
        # testing              
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrIpAddrPrefix",  "IpAddress") 
        for subnet, netmask, next_hop, peer in data:
            if subnet not in bgp_data:
                bgp_data[subnet] = {}
            bgp_data[subnet]["Netmask"] = netmask
        
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrnext_hop",  "IpAddress")  
        for subnet, netmask, next_hop, value in data:
            if "next_hop" not in bgp_data[subnet]:
                bgp_data[subnet]["next_hop"] = {}
            bgp_data[subnet]["next_hop"][next_hop] = {}
        
        #TODO: find more concise way to do this mapping  (lambda style etc)
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrLocalPref",  "INTEGER") 
        for subnet, netmask, next_hop, value in data:
            bgp_data[subnet]["next_hop"][next_hop]["LocalPref"] = value  
        
        
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrBest",  "INTEGER")   
        for subnet, netmask, next_hop, value in data: 
            # Capitalise True/False value to allow easier
            #  boolean comparison later
            bgp_data[subnet]["next_hop"][next_hop]["Best"] = value.capitalize()
            
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrMultiExitDisc",  "INTEGER")  
        for subnet, netmask, next_hop, value in data:
            bgp_data[subnet]["next_hop"][next_hop]["MED"] = value
                
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrOrigin",  "INTEGER")       
        for subnet, netmask, next_hop, value in data:
            bgp_data[subnet]["next_hop"][next_hop]["Origin"] = value 
            
        #TODO: see if want to use this, or peer    
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrnext_hop",  "IpAddress")
        for subnet, netmask, next_hop, value in data:
            bgp_data[subnet]["next_hop"][next_hop]["next_hop"] = value
            
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrPeer",  "IpAddress") 
        for subnet, netmask, next_hop, value in data:
            bgp_data[subnet]["next_hop"][next_hop]["Peer"] = value  
        
        data = self.parse_snmp_key(ssh_link, tap_ip,
            "BGP4-MIB:bgp4PathAttrASPathSegment",  "HexString")    
        for subnet, netmask, next_hop, segments in data:
            
                                                     
            segments = segments.split()
                # need to extract as pairs  
            aspath = []        
            #remove first two elements, as these are the size, and the length
            # refer http://tools.cisco.com/Support/SNMP/do/BrowseOID.do? \
            #local=en&translate=Translate&objectInput=bgp4PathAttrASPathSegment
            path_type = segments.pop(0)
            length = segments.pop(0)  
            length = int(length)    
            bgp_data[subnet]["next_hop"][next_hop]["PathLength"] = length    

            while len(segments) > 0:  
                # pop removes from end of list TODO: check and clean this up
                seg_x = segments.pop(0)
                seg_y = segments.pop(0)       
                seg_z = int(seg_x, 16)*256 + int(seg_y, 16) 
                aspath.append(seg_z) 
                #aspath.append((hex(x)*256) + hex(y))                          
                                                                
            # add path to dictionary  
            bgp_data[subnet]["next_hop"][next_hop]["ASPath"] = aspath        
        
        #pp = pprint.PrettyPrinter()
        #pp.pprint(bgp_data) 
        
        # plot      
        plot_as_path(bgp_data, host)
        return
        
                
    def parse_snmp_key(self, ssh_link, host, snmp_key,  regex_type):
        #TODO: replace format with % 
        ssh_link.sendline("snmpwalk -c public -v1 {0} {1}".format(
            host, snmp_key))  
        LOGGER.debug("Querying {0}".format(snmp_key)) 
                                                        
        #TODO: use multiline regexes
        if(regex_type == "INTEGER"):
            regex = ".(\d+.\d+.\d+.\d+).(\d+).(\d+.\d+.\d+.\d+) \
                = INTEGER: (\w+)"
        elif(regex_type == "IpAddress"):
            regex = ".(\d+.\d+.\d+.\d+).(\d+).(\d+.\d+.\d+.\d+) \
                = IpAddress: (\d+.\d+.\d+.\d+)"
        elif(regex_type == "HexString"):
            regex = "(\d+.\d+.\d+.\d+).(\d+).(\d+.\d+.\d+.\d+) \
                = Hex-STRING: ((?:[0-9A-F]{2} [0-9A-F]{2} ?)+)"       
                                                             
        # Dict key is the end of the snmp key, so remove the start
        #TODO: remove this, no longer used
        return_list = []

        cpl = ssh_link.compile_pattern_list([ssh_link.PROMPT, regex])
        while 1:      
            i = ssh_link.expect_list(cpl)       
            if i == 0:
                # Got netkit prompt, finished with snmp
                break
            elif i == 1:         
                # add to dictionary              
                subnet = ssh_link.match.group(1)  
                netmask = ssh_link.match.group(2) 
                next_hop = ssh_link.match.group(3)
                value = ssh_link.match.group(4) 
                return_list.append( (subnet, netmask, next_hop, value) ) 
                
        return return_list
