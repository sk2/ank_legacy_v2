%for name, route_map_items in route_maps.items():    

%for (seq_no, match_clause, action_clause, reject) in route_map_items:        
% if reject:
   route-map ${name} deny ${seq_no} 
%else:
     route-map ${name} permit ${seq_no} 
% endif
    %for (match_type, comparison, match_value) in match_clause:
        % if match_type == "prefix_list":
        match ip address prefix_list ${match_value}
        % elif match_type == "tag":
        match community_list ${match_value}
        % endif      
    %endfor  
    %for (action_type, action_value) in action_clause:
        % if action_type == "addTag":
        set community ${action_value}
        % elif action_type == "setLP":
        set local-preference ${action_value}       
        % elif action_type == "setNextHop":
        set ip next-hop ${action_value}       
        % elif action_type == "removeTag":  
        ! Note: this needs to be a community list (created) not the commvalue
        set comm-list ${action_value} delete;
        % endif      
    %endfor    
!
%endfor            


%endfor
