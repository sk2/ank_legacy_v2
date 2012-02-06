!
hostname ${hostname}
password ${password}              
banner motd file /etc/quagga/motd.txt
!enable password ${enable_password}
! 
router bgp ${asn}
 no synchronization
% for i in sorted(interfaces, key = lambda x: x['network']):
 network ${i['network']} mask ${i['netmask']}
% endfor
% for groupname, group_data in bgp_groups.items():     
 % if group_data['type'] == 'internal' or group_data['type'] == 'external':   
  % for neighbor in sorted(group_data['neighbors'], key = lambda x: x['id']):
   % if group_data['type'] == 'internal':
 neighbor ${neighbor['id']} remote-as ${asn}
 neighbor ${neighbor['id']} update-source ${identifying_loopback.ip}
   % else:
 neighbor ${neighbor['id']} remote-as ${neighbor['peer_as']} 
   % endif
   % if neighbor['route_maps_in']:
 neighbor ${neighbor['id']} route-map ${neighbor['route_maps_in']} in   
   % endif
   % if neighbor['route_maps_out']:
 neighbor ${neighbor['id']} route-map ${neighbor['route_maps_out']} out
   % endif
   % if 'internal_rr' in groupname:
 neighbor ${neighbor['id']} route-reflector-client
   % endif
  % endfor
 % endif
% endfor
% if 'cluster' in group_data:
 bgp cluster-id ${group_data['cluster']}
% endif
!
% for name, values in sorted(policy_options['community_lists'].items()):
 % if isinstance(values, str):   
ip community-list standard ${name} permit ${values}
 % else:
  % for value in values:
ip community-list standard ${name} permit ${value}
  % endfor
 %endif
% endfor    
!
% for name, values in sorted(policy_options['prefix_lists'].items()):
 % for (index, prefix) in enumerate(values, start=1):
ip prefix-list ${name} seq ${index * 5} permit ${prefix}
 % endfor
% endfor 
!       
% for rm_name, match_tuples in sorted(policy_options['route_maps'].items()):
  % for index, match_tuple in enumerate(match_tuples, start=1):
    % if match_tuple.reject:
route-map ${rm_name} deny ${index * 10}
    % else:
route-map ${rm_name} permit ${index * 10}
    % endif
    % if len(match_tuple.match_clauses):
      % for match_clause in match_tuple.match_clauses:
        % if match_clause.type == "prefix_list":
 match ip address prefix-list ${match_clause.value};
        % elif match_clause.type == "tag":   
          % if isinstance(match_clause.type, str):   
 match community ${match_clause.value}
          % elif isinstance(match_clause.type, dict):
            % for match in match_clause.value: 
 match community ${match}
            % endfor
          %endif
        % endif      
       % endfor
     % endif
    %if len(match_tuple.action_clauses) or match_tuple.reject:
      %for action_clause in match_tuple.action_clauses:
        % if action_clause.action == "addTag":
 set community ${policy_options['community_lists'][action_clause.value]} additive
	% elif action_clause.action == "setLP":
 set local-preference ${action_clause.value}
	% elif action_clause.action == "setMED":
 set metric ${action_clause.value}
	% elif action_clause.action == "setNextHop":
 set ip next-hop ${action_clause.value}
	% elif action_clause.action == "removeTag":
 set comm-list ${action_clause.value} delete
	% endif     
      %endfor   
    % endif         
	% if index < len(match_tuples):
 on-match goto ${(index*10)+1}
	% endif
 % endfor   
route-map ${rm_name} permit ${(index+1)*10}
!
% endfor
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
