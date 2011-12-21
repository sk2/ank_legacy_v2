!
hostname ${hostname}
password ${password}              
banner motd file /etc/quagga/motd.txt
!enable password ${enable_password}
! 
router bgp ${asn}
	bgp router-id ${router_id}     
	redistribute kernel
    redistribute connected
   	!
	! Networks
	% for n in network_list:  
	network ${n}
        aggregate-address ${n} summary-only
	%endfor
	!      
	% if route_reflector:       
	! Route-Reflector
	bgp cluster-id ${router_id}       
	!
	% endif
	% if len(ibgp_neighbor_list) > 0:
	% endif               
	% if len(ibgp_rr_client_list):       
	! Route-Reflector clients
	% endif      
	% for n in ibgp_rr_client_list:
	neighbor ${n['remote_ip']} route-reflector-client    
	neighbor ${n['remote_ip']} remote-as ${asn}
	neighbor ${n['remote_ip']} update-source ${router_id}  
	neighbor ${n['remote_ip']} description ${n['description']} (iBGP) 
	% endfor
	!           
	! iBGP neighbors  
	% for n in ibgp_neighbor_list:
	neighbor ${n['remote_ip']} remote-as ${asn}
	neighbor ${n['remote_ip']} update-source ${router_id}  
	neighbor ${n['remote_ip']} description ${n['description']} (iBGP) 
	% endfor
	!
	% if len(ebgp_neighbor_list) > 0:
	#eBGP neighbors   
	% endif
	% for n in ebgp_neighbor_list:
	neighbor ${n['remote_ip']} remote-as ${n['remote_as']} 
	neighbor ${n['remote_ip']} description ${n['description']} (eBGP)   
	% if "route_map_in" in n and n['route_map_in'] != None:
	neighbor ${n['remote_ip']} route-map rm-${n['route_map_in']} in     
	% endif   
	% if "route_map_out" in n and n['route_map_out'] != None:
	neighbor ${n['remote_ip']} route-map rm-${n['route_map_out']} out  
	% endif        
	!
	% endfor
	!       
	
	! Route-maps 
	% for category, maps in route_maps.items():
	! ${category}
	% for map in maps:   
	route-map rm-${map['id']} permit ${map['order']}
	    %if "description" in map:
	    description ${map['description']}
	    %endif  
	    %if "match-access-list" in map:
	    match ip address al-${map['match-access-list']}
	    %endif
	    %if "match-community" in map:
	    match community cm-${map['match-community']}
	    %endif
	    %if "set-community" in map:
	    set community ${map['set-community']}
	    %endif  
	    %if "local-preference" in map:
	    set local-preference ${map['local-preference']}
	    %endif
	    %if "ip next-hop" in map:
	    set ip next-hop ${map['ip next-hop']}
	    %endif   
	    %if "call-list" in map:  
		% for c in map['call-list']:
		call rm-${c}
		%endfor
	    %endif

    %endfor          

	%endfor 
    
	! Community lists  
	% for community, label in sorted(communities_dict.items()):
	ip community-list standard cm-${label} permit ${community}   
	%endfor    
	
	! Access lists  
	% for label, prefix in sorted(access_list):
	access-list al-${label} permit ${prefix['cidr']}   
	%endfor
	
    

%if use_debug:
!
debug bgp events
debug bgp filters
debug bgp updates 
debug bgp zebra
!
%endif   

%if dump:
!
! dump bgp all /var/log/zebra/bgpdump.txt
dump bgp routes-mrt /var/log/zebra/bgproutes.dump  
!
%endif    

%if use_snmp:
!
smux peer .1.3.6.1.4.1.3317.1.2.2 quagga_bgpd
!
%endif


log file /var/log/zebra/bgpd.log

