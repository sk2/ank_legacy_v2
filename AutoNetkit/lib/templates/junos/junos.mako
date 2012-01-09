system {
    host-name ${hostname}; 
    root-authentication {
        encrypted-password "$1$SGUyJfYE$r5hIy2IU4IamO1ye3u70v0";
    }
    name-server {
        8.8.8.8;
    }
    login {
        message "Welcome to the cloud\npassword is Clouds\nConfiguration generated on ${date} by AutoNetkit ${ank_version} ";
    }
    services {
        finger;
        ftp;
        rlogin;
        rsh;
        ssh;
        telnet;
        xnm-clear-text;
    }
    syslog {
        host log {
            kernel info;
            any notice;
            pfe info;
            interactive-commands any;
        }
        file messages {
            kernel info;
            any notice;
            authorization info;
            pfe info;
            archive world-readable;
        }
        file security {
            interactive-commands any;
            archive world-readable;
        }
    }
    processes {
        routing enable;
        management enable;
        watchdog enable;
        snmp enable;
        inet-process enable;
        mib-process enable;
    }
}
interfaces {
    % for i in interfaces:
    ${i['id']} {
        unit 0 {          
	        description "${i['description']}";
            family inet {      
                address ${i['ip']}/${i['prefixlen']};
            }                 
			% if 'net_ent_title' in i:  
			family iso {
				address ${i['net_ent_title']}
			}   
			% elif igp_protocol == 'isis':
			family iso;
			% endif
        }
    }
    %endfor 
}            

routing-options {
    aggregate {
        route 
		%for n in network_list:  
		${n};
		%endfor  
    }
    router-id ${router_id};
    autonomous-system ${asn};
} 
     
protocols {             
	% if igp_protocol == 'ospf':
	ospf {
	        area 0.0.0.0 {
			% for i in igp_interfaces:
				  % if 'passive' in i:   
				interface ${i['id']}  {
						passive;   
					}
				% else:
				interface ${i['id']};
			  % endif                
			%endfor
	    }
	}                      
	% elif igp_protocol == 'isis':
	isis {               
		level 2 wide-metrics-only;
		level 1 disable;
		% for i in igp_interfaces:   
		% if i['id'].startswith('lo'):
		interface ${i['id']};
		% else:
		interface ${i['id']}  {
			point-to-point;   
			% if 'weight' in i:
			level 2 metric ${i['weight']};
			% endif
		}                        
		% endif
		%endfor    
	}                      
	% endif    
	% if bgp_groups:         
	bgp {                  
		export adverts;
		% for groupname, group_data in bgp_groups.items():   
			group ${groupname} {
				type ${group_data['type']};    
				% if group_data['type'] == 'internal':
			    local-address ${router_id};           
			    % endif
			    % if 'cluster' in group_data:
			    cluster ${group_data['cluster']}
			    % endif
			    % for neighbor in group_data['neighbors']: 
				   % if 'peer_as' in neighbor or len(neighbor['route_maps_in']) or len(neighbor['route_maps_out']):      
			    neighbor  ${neighbor['id']} {  
				 % if 'peer_as' in neighbor:
					peer-as ${neighbor['peer_as']};
				%endif             
				 % if len(neighbor['route_maps_in']) == 1:   
					import ${neighbor['route_maps_in'].pop()};
				 % elif len(neighbor['route_maps_in']) > 1:
					import [${" ".join(neigh for neigh in neighbor['route_maps_in'])}];
				%endif  
				 % if len(neighbor['route_maps_out']) == 1:      
  					export ${neighbor['route_maps_out'].pop()};
				 % elif len(neighbor['route_maps_out']) > 1:
					export [${" ".join(neigh for neigh in neighbor['route_maps_out'])}];
				%endif
				}                          
				   % else:          
			    neighbor  ${neighbor['id']};
				   % endif
				% endfor
			}
		% endfor
	}
	% endif           
}                  

policy-options {     
	% for name, values in sorted(policy_options['community_lists'].items()):     
 	% if isinstance(values, str):   
	community ${name} members ${values};
	 % else:
	community ${name} members [${" ".join(val for val in values)}];
	%endif
	% endfor         
	
	% for name, values in sorted(policy_options['prefix_lists'].items()): 
	prefix-list ${name} {
	    % for prefix in values: 
			${prefix};
		% endfor
	 }
	% endfor    
	%for route_map in policy_options['route_maps']:    
	policy-statement ${route_map.name} { 
		%for match_tuple in route_map.match_tuples:        
		term ${match_tuple.seq_no * 10} {
		    %if len(match_tuple.match_clauses):
		    from  {
		    %for match_clause in match_tuple.match_clauses:
		        % if match_clause.type == "prefix_list":
		        prefix-list ${match_clause.value};
		        % elif match_clause.type == "tag":   
				 	% if isinstance(match_clause.type, str):   
				community ${match_clause.value};
				 	% else:    
				community [${" ".join(val for val in match_clause.value)}];
					%endif
		        % endif      
		    %endfor
		    }
		    % endif             
		    %if len(match_tuple.action_clauses) or match_tuple.reject: 
		    then {                    
		    %for action_clause in match_tuple.action_clauses:
		        % if action_clause.action == "addTag":
		        community add ${action_clause.value};
		        % elif action_clause.action == "setLP":
		        local-preference ${action_clause.value};   
		        % elif action_clause.action == "setMED":
		        metric ${action_clause.value};   
		        % elif action_clause.action == "setNextHop":
		        next-hop ${action_clause.value};  
		        % elif action_clause.action == "removeTag":
		        community delete ${action_clause.value};
		        % endif     
		    %endfor   
		    % if match_tuple.reject:
		        reject;
		    % else: 
		        accept;
		   % endif
		    } 
		    % endif 
		} 
	%endfor            
	}
	%endfor
	
	
    policy-statement adverts {
        term 1 {
            from protocol [ aggregate direct ];
            then accept;
        }
    }
}
