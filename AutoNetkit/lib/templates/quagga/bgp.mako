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
	% for i in interfaces:
    network ${i['network']} mask ${i['netmask']}
        % endfor
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
	% if n.get('route_map_in'):
	neighbor ${n['remote_ip']} route-map ${n['route_map_in']} in     
	% endif   
	% if n.get('route_map_out'):
	neighbor ${n['remote_ip']} route-map ${n['route_map_out']} out  
	% endif
	% endfor
	!
	% if len(ebgp_neighbor_list) > 0:
	#eBGP neighbors   
	% endif            
	% for n in ebgp_neighbor_list:
	neighbor ${n['remote_ip']} remote-as ${n['remote_as']} 
	neighbor ${n['remote_ip']} description ${n['description']} (eBGP)   
	% if n.get('route_map_in'):
	neighbor ${n['remote_ip']} route-map ${n['route_map_in']} in     
	% endif   
	% if n.get('route_map_out'):
	neighbor ${n['remote_ip']} route-map ${n['route_map_out']} out  
	% endif        
	!
	% endfor
	! Route-map call-groups 
	% for name, members in route_map_call_groups.items():    
	route-map ${name} permit 10
		% for member in members:
		call ${member}
		on-match next
		%endfor 
	!	
	%endfor    
	! Route-maps
%for route_map in route_maps:    
%for match_tuple in route_map.match_tuples:        
% if match_tuple.reject:
    route-map ${route_map.name} deny ${match_tuple.seq_no}             
	!TODO: rejected, need to continue to next seqno
%else:
    route-map ${route_map.name} permit ${match_tuple.seq_no} 
% endif
    %for match_clause in match_tuple.match_clauses:
        % if match_clause.type == "prefix_list":
        match ip address ${match_clause.value}
        % elif match_clause.type == "tag":
        match community ${match_clause.value}
        % endif      
    %endfor  
    %for action_clause in match_tuple.action_clauses:
        % if action_clause.action == "addTag":
        set community ${community_lists[action_clause.value]}
        % elif action_clause.action == "setLP":
        set local-preference ${action_clause.value} 
        % elif action_clause.action == "setMED":
        set metric ${action_clause.value}      
        % elif action_clause.action == "setNextHop":
        set ip next-hop ${action_clause.value}       
        % elif action_clause.action == "removeTag":  
        ! Note: this needs to be a community list (created) not the commvalue
        set comm-list ${action_clause.value} delete
        % endif      
    %endfor    
	!
%endfor            
%endfor  
	! Community lists  
	% for name, communities in sorted(community_lists.items()):  
	% if isinstance(communities, str):      
	ip community-list standard ${name} permit ${communities}   
	 % else:
		% for community in communities:
	ip community-list standard ${name} permit ${community}   
		% endfor	
		%endif      
	%endfor                     
	! Prefix lists  
	% for name, prefixes in sorted(prefix_lists.items()):     
		% for prefix in prefixes:
	ip prefix-list standard ${name} permit ${prefix}   
		% endfor
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
