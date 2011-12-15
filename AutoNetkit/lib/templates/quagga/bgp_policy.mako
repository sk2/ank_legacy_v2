%for route_map in route_maps:    
!
%for (seq_no, match_tuple) in route_map.match_tuples:        
% if match_tuple.reject:
     route-map ${route_map.name} deny ${seq_no}             
	!TODO: rejected, need to continue to next seqno
%else:
     route-map ${route_map.name} permit ${seq_no} 
% endif
    %for match_clause in match_tuple.match_clauses:
        % if match_clause.type == "prefix_list":
        match ip address prefix_list ${match_clause.value}
        % elif match_clause.type == "tag":
        match community_list ${match_clause.value}
        % endif      
    %endfor  
    %for action_clause in match_tuple.action_clauses:
        % if action_clause.action == "addTag":
        set community ${action_clause.value}
        % elif action_clause.action == "setLP":
        set local-preference ${action_clause.value}       
        % elif action_clause.action == "setNextHop":
        set ip next-hop ${action_clause.value}       
        % elif action_clause.action == "removeTag":  
        ! Note: this needs to be a community list (created) not the commvalue
        set comm-list ${action_clause.value} delete;
        % endif      
    %endfor    
!
%endfor            
%endfor
