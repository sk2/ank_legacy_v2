hostname ${hostname}
!
boot-start-marker
boot-end-marker
!
!
no aaa new-model
!
!
ip cef
!
% for i in interfaces:
interface ${i['id']}
 description ${i['description']}
 ip address ${i['ip']} ${i['netmask']} 
 % if igp_protocol == 'isis':
 ip router isis
   % if 'weight' in i:
 isis metric ${i['weight']}
   % endif
 % else:
   % if 'weight' in i:
 ip ospf cost ${i['weight']}
   % endif
 % endif
 no shutdown
 duplex auto
 speed auto
!
!
%endfor
!
% if igp_protocol == 'isis':
  % for i in interfaces:
    % if 'net_ent_title' in i:
router isis ${i['net_ent_title']}
    % endif
  % endfor
  % for i in igp_interfaces:
    % if 'passive' in i:
 passive-interface ${i['id']}
    % endif
  % endfor
 redistribute connected
 redistribute static ip
% elif igp_protocol == 'ospf':
router ospf 1
 redistribute connected
 redistribute static
  % for i in igp_interfaces:
 network ${i['network']} ${i['wildcard']} area ${i['area']}
    % if 'passive' in i:
 passive-interface ${i['id']}
    % endif
  % endfor
% endif
!
!
router bgp ${asn}
 no synchronization
% for i in interfaces:
 network ${i['network']} mask ${i['netmask']}
% endfor
% for groupname, group_data in bgp_groups.items():
 % if group_data['type'] == 'internal':
  % for neighbor in group_data['neighbors']:
 neighbor ${neighbor['id']} remote-as ${asn}
 neighbor ${neighbor['id']} update-source loopback 0
 neighbor ${neighbor['id']} send-community
   % if neighbor['route_maps_in']:
 neighbor ${neighbor['id']} route-map ${neighbor['route_maps_in'].pop()} in
   % elif neighbor['route_maps_out']:
 neighbor ${neighbor['id']} route-map ${neighbor['route_maps_out'].pop()} out
   % endif

   % if 'internal_rr' in groupname:
 neighbor ${neighbor['id']} route-reflector-client
   % endif
  % endfor
 % elif group_data['type'] == 'external':
  % for neighbor in group_data['neighbors']:
 neighbor ${neighbor['id']} remote-as ${neighbor['peer_as']}
 neighbor ${neighbor['id']} send-community
  % endfor
 % endif
% endfor
% if 'cluster' in group_data:
 bgp cluster-id ${group_data['cluster']}
% endif

ip forward-protocol nd
!
no ip http server
!
ip bgp-community new-format
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
 % for prefix in values: 
ip prefix-list ${name} seq 5 permit ${prefix}
 % endfor
% endfor 
!       
! Route-map call-groups 
% for name, members in sorted(policy_options['route_map_call_groups'].items()):    
route-map ${name} permit 10
	% for member in members:
	call ${member}
	on-match next
	%endfor 
!            
%endfor 
% for route_map in sorted(policy_options['route_maps']):
  % for match_tuple in route_map.match_tuples:
    % if match_tuple.reject:
route-map ${route_map.name} deny ${match_tuple.seq_no * 10}
    % else:
route-map ${route_map.name} permit ${match_tuple.seq_no * 10}
    % endif
    % if len(match_tuple.match_clauses):
      % for match_clause in match_tuple.match_clauses:
        % if match_clause.type == "prefix_list":
 match ip address prefix-list ${match_clause.value};
        % elif match_clause.type == "tag":   
          % if isinstance(match_clause.type, str):   
 match community ${match_clause.value};
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
 % endfor
!
% endfor
