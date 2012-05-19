# -*- coding: utf-8 -*-
"""
Deploy a given Netkit lab to a Netkit server
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

import logging
LOG = logging.getLogger("ANK")
                                 
import itertools
import os     
import re
import time
import AutoNetkit.config as config
import textfsm
import pprint
from pkg_resources import resource_filename
import AutoNetkit as ank

# Used for EOF and TIMEOUT variables
try:
    import pexpect
except ImportError:
    LOG.error("Netkit deployment requires pexpect")

class NetkitDeploy():  
    """ Deploy a given Netkit lab to a Netkit server"""
    
    def __init__(self, server, lab_dir, network, xterm=False, host_alias=None):
        self.server = server
        self.lab_dir = lab_dir
        self.network = network
        self.xterm = xterm
        self.host_alias = host_alias
    
    def deploy(self): 
        """ Deploys lab_dir to Netkit server""" 
        # stops lab, copies new lab over, starts lab 
        
        shell = self.server.get_shell()   
        server = self.server
        #TODO: throw/catch exceptions instead of warning and errors  

        if not shell:
            # Problem has occured, end deployment
            LOG.warn("Unable to connect to Netkit host. Ending deployment.")
            return  

        if not server.check_nk_installed():
            LOG.warn("Netkit environment variable not found. "
                "Please check Netkit is correctly installed.")
            return 
        else:
            LOG.debug("Netkit environment variable found, proceeding")

        if not server.check_tunnel():
            LOG.warn("Netkit TAP tunnel not setup. "
                "Please manually configure.")
            return 
        else:                 
            LOG.debug("Netkit TAP tunnel present, proceeding")

        self.stop_lab()       
        
        if not server.local_server:
            # Netkit on remote server, need to transfer lab over
            self.archive_and_transfer_lab()
        
        self.start_lab()

    def stop_lab(self):  
        return
        """Halts running Netkit lab"""

        LOG.info(  "Halting previous lab" )
        server = self.server
        shell = self.server.get_shell()   
        lab_dir = self.lab_dir

        # See if lab folder exists (or if fresh installation)       
        # check for remote directory
        if not server.local_server:
            # only applicable for remote (ie copied over) labs
            shell.sendline("[ -d " + lab_dir + 
                " ] && echo 'Present' || echo 'Absent'\n")
            shell.prompt() 
            result = shell.before 
            # Examine result line by line 
            # (as command itself is also often echoed back)  
            for line in result.splitlines():
                if line == "Absent":
                    # Folder doesn't exist => no Lab to stop      
                    LOG.debug("Lab directory doesn't exist, no lab to stop") 
                    shell.sendline()
                    shell.prompt() 
                    return    

        #stop lab     
        shell.sendline("cd " + lab_dir)
        
        # Use -q flag to shutdown hosts quickly     
        shell.sendline("lhalt -q")
        # Pattern: Halting "AS1r1"...
        pattern = "Halting \"(\w+)\"..."   
        finished = "Lab has been halted."
        # Limit max lines to 1000
        for dummy in range (0, 1000):
            i = shell.expect ([pattern, finished, pexpect.EOF])
            if i == 0:
                LOG.debug(  "Halted host " + shell.match.group(1)    )  
            elif i == 1: 
                LOG.debug(  "Finished halting lab"    ) 
                break
            else:    
                break # reached end
        return  
    

    def archive_and_transfer_lab(self):
        """Archives lab, transfers to remote server, and extracts""" 
        
        LOG.info("Copying Lab over")    
                                        
        # Archive current lab
        tar_file = os.path.join(config.ank_main_dir, self.network.compiled_labs['netkit'])
        # Transfer to remote server  
        self.server.transfer_file(tar_file)
               
        shell = self.server.get_shell()
        # Remove previous lab if present on remote server   
        shell.sendline("cd ")
        shell.prompt() 
        shell.sendline("rm -rf  " + self.lab_dir + "/*")
        shell.prompt() 
        LOG.debug(  "Removed previous lab directory" )

#TODO: check why get " ar: Removing leading `/' from member names" on Linux

        # Extract new lab
        #_, tarfilename = os.path.split(tar_file)
        #tar_filename, _ = os.path.splitext(filename)
        tar_basename = os.path.basename(tar_file)
        shell.sendline("tar -xzf  " + tar_basename)
        shell.prompt() 
        LOG.debug(  "Extracted new lab"  )
        
        return 
          

    def start_lab(self):   
        """Starts Netkit lab.
            Will also copy across lab if Netkit host is remote"""        
        lab_dir = self.lab_dir
        LOG.info(  "Starting lab" )
        shell = self.server.get_shell()
        shell.sendline("cd " + lab_dir)

        machine_list = self.lab_host_list()

        # Check virtual machines have been halted 
        LOG.info("Checking all previous machines shutdown") 
        self.confirm_hosts_shutdown(machine_list)  
        LOG.debug("All required hosts shutdown, proceeding")

        # Start lab   
        LOG.info( "All previous machines shutdown, starting lab")
        # Parameters: 5 machines at a time, no console
        if self.xterm:
            # Start with each VM console in Xterm (vstart/lstart default)
            shell.sendline("lstart -p5")
        else:
            # Start with console disabled (access via SSH only)
            shell.sendline("lstart -p5 -o --con0=none")

        # Start infinite loop, as don't know how many lines to expect.
        # Leave when receive correct output
        current_machine_index = 1             
        while 1:      
            i = shell.expect([
                "The lab has been started.",    # Completed
                'Starting "(\w+)"...',
                'vstart: Virtual machine "(\w+)" is already running.',
                pexpect.TIMEOUT,
                pexpect.EOF,
                "Terminated",
                "Error while configuring the tunnel.",
                ])   

            if i == 0:     
                # Finished starting lab 
                status =  ("Finished starting Lab, "
                    "{0} machines started").format(len(machine_list)) 
                LOG.info(  status  )  
                # Leave infinite loop
                break                                                    

            elif i == 1:     
                # Starting hosts             
                status = "Starting {0} ({1}/{2})".format( 
                    shell.match.group(1), current_machine_index,
                    len(machine_list))
                LOG.info(  status  )  
                current_machine_index += 1 
                   
            elif i == 2:
                # Some hosts still running. Should have been shutdown already.
                vhost = shell.match.group(1)
                LOG.warn(("Error starting lab, machine {0}"
                    "is still running").format(vhost))
            
            elif i == 3:       
                #TODO: behaviour here?
                LOG.debug( "timeout"  )  
                
            elif i == 4:              
                #TODO: behaviour here?
                LOG.debug( "EOF" )     
                
            elif i == 5:    
                LOG.warn("An error has occurred, startup terminated.")   
                return                                          
                
            elif i == 6:  
                # Problem starting tunnel. Tunnel should already be
                # present.                                                      
                #TODO integrate this with the setup tap tunnel function   
                pass

        #TODO check all machines are running, similar to checking they 
        # were shutdown. Can then do fast (ie no checking) startup

        return 

    def lab_host_list(self):
        # reads Lab host list from file, as pxssh can have problems with large
        # buffers, so large networks will hang on the lab read stage
        lab_conf_file = open("{0}/{1}".format(self.lab_dir, "lab.conf"), 'r')
        machine_list = []
        for line in lab_conf_file:
            # Faster to use string operations than regexps
            if "[" in line:
                # Host is part up to the [x] eg  1_Rome[0]=10.0.1.232.30
                host_name = line[:line.find("[")]
                machine_list.append(host_name)
        # Make unique
        return list(set(machine_list))

    
    def get_lab_host_list(self): 
        """ Uses Netkit command to get list of hosts in lab"""
        shell = self.server.get_shell()
        shell.sendline("linfo")
        machine_list = []
        # Limit max lines to 500
        for dummy in range (0, 1000):
            i = shell.expect ([    
                # Netkit output stating lab machine count
                "of (\d+) virtual machines \( ((?:\w+ ?)+\w+)\)",
                pexpect.EOF,
                ])
            if i == 0:
                machine_list = shell.match.group(2)
                machine_list = machine_list.split()
                LOG.debug("hosts in lab are: " + ", ".join(machine_list) )  
                break
            else:    
                # reached end of file
                #TODO: double check what should be done if get to here
                print "EOF"
                break
        return machine_list

    def confirm_hosts_shutdown(self, host_list):   
        """ Shuts down any machines in host_list which are still running"""
        shell = self.server.get_shell()
        
        #  sknight          taptunnelvm        1471      41632  
        pattern = "\w+\s+(\w+)\s+\d+\s+\d+"    
        # The last line of vlist output
        last_line = "\nTotal virtual machines"

        can_proceed = True     
        # Keep looping until all required hosts shutdown
        while 1:
            can_proceed = True      
            # See which machines are currently running
            shell.sendline("vlist ")    
            
            # Limit max lines to 1000 
            # Loop to analyse output   
            for dummy in range (0, 1000):  
                i = shell.expect ([pattern, pexpect.EOF, last_line])   
                if i == 0:
                    vhost = shell.match.group(1)  
                    if vhost in host_list:            
                        LOG.debug( "Machine " + vhost + 
                            " is in list of machines that should be shutdown" )
                        can_proceed = False
                        # Tell this machine to shutdown
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
                LOG.info(("Some hosts still running, retrying in "
                    "{0} seconds").format(delay))
                time.sleep(delay)
        return    

    def collect_data(self, commands):
        shell = self.server.get_shell()
        shell.setecho(False)

        collected_data_dir = config.collected_data_dir
        netkit_data_dir = os.path.join(collected_data_dir, "netkit")
        if not os.path.isdir(netkit_data_dir):
                os.mkdir(netkit_data_dir)
        host_data_dir = os.path.join(netkit_data_dir, self.host_alias)
        if not os.path.isdir(host_data_dir):
                os.mkdir(host_data_dir)
        collect_timestamp_dir = os.path.join(host_data_dir, time.strftime("%Y%m%d_%H%M%S", time.localtime()))
        if not os.path.isdir(collect_timestamp_dir):
            os.mkdir(collect_timestamp_dir)

        servers = set(self.network.servers())

        #TODO: need to have way to allow privexec.... or just disable enable password?
#TODO: Put term len 0 into configs

        for node in self.network.devices():
            routername = ank.fqdn(self.network, node)
            full_routername = ank.rtr_folder_name(self.network, node)
            user_exec_prompt = "%s>" % node.dns_hostname
            priv_exec_prompt = "%s#" % node.dns_hostname
            for port_command in commands:
                LOG.info("%s: running %s" % (routername, port_command))
                telnet_port, command = port_command.split(":")
                if telnet_port == 'ssh':
                    self.server.connect_vm(node.tap_ip, shell)
                    shell.sendline(command)
                    shell.expect(self.server.NETKIT_PROMPT)
                    command_output = shell.before
                    self.server.disconnect_vm(shell)
                    shell.prompt()
# need to ssh into this machine
                else:
                    if node in servers:
# don't try telnet into as zebra not running
                        continue
# use telnet
                    shell.sendline("telnet %s %s" % (node.tap_ip, telnet_port))
                    shell.expect("Password:")
                    shell.sendline("1234")
                    shell.expect(user_exec_prompt)
                    shell.sendline("en")
                    i = shell.expect(["Password:", priv_exec_prompt])
                    if i == 0:
                        shell.sendline("1234")
                    else:
# all good, in priv exec
                        pass
# just to be sure
                    set_term_length = "term len 0"
                    shell.sendline(set_term_length)
                    shell.expect(priv_exec_prompt)
                    shell.sendline(command)
                    shell.expect(priv_exec_prompt)
# Can be an issue with the telnet x zebra command (not for bgpd it seems)
                    command_output = shell.before
# If no command output, captured the previous command, try again
                    if command_output.strip() == set_term_length:
                        shell.expect(priv_exec_prompt)
                        command_output = shell.before
                    shell.sendline("exit")
                    shell.prompt() 
# from http://stackoverflow.com/q/295135/
                command_filename_format = (re.sub('[^\w\s-]', '', command).strip().lower())
                filename = "%s_%s_%s.txt" % (full_routername,
                        command_filename_format,
                        time.strftime("%Y%m%d_%H%M%S", time.localtime()))
                filename = os.path.join(collect_timestamp_dir, filename)
                
                with open( filename, 'w') as f_out:
                    f_out.write(command_output)
                # check back at linux shell before continuing


    def traceroute(self, src_dst_list):
        shell = self.server.get_shell()
        shell.setecho(False)

        template_dir =  resource_filename("AutoNetkit","lib/templates")
        linux_traceroute_template = open(os.path.join(template_dir, "textfsm", "linux_traceroute"), "r")
        re_table = textfsm.TextFSM(linux_traceroute_template)

# build reverse-IP lookup
        ip_mappings = {}
        ip_mappings.update( dict( (device.lo_ip.ip, device.hostname) 
            for device in self.network.devices()))
        for link in self.network.links():
            ip_mappings[link.local_ip] = link.local_host
            ip_mappings[link.remote_ip] = link.remote_host

#convert pairs list into 2-tuples, eg [1, 2, 3, 4, ...] -> (1, 2), (3, 4), ...
        label_pairs = [ (src_dst_list[i], src_dst_list[i+1])
                for i in range(0, len(src_dst_list), 2)]
        for src_label, dst_label in label_pairs:
            try:
                src = self.network.find(src_label)
            except ank.network.DeviceNotFoundException:
                LOG.warn("Unable to find device %s" % src_label)
                continue
            try:
                dst = self.network.find(dst_label)
            except ank.network.DeviceNotFoundException:
                LOG.warn("Unable to find device %s" % dst_label)
                continue

            LOG.info("Tracing from %s to %s" % (src_label, dst_label))
            self.server.connect_vm(src.tap_ip, shell)
            #TODO: make this handle appropriate ID for servers (no lo_ip)
# TODO: probably be st to integrate into the device namedtuple for consistency
            shell.sendline("traceroute -n %s" % dst.lo_ip.ip)
            shell.expect(self.server.NETKIT_PROMPT)
            command_output = shell.before
            self.server.disconnect_vm(shell)
            shell.prompt()
            print command_output
            print "result", re_table.ParseText(command_output)
