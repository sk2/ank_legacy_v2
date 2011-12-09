%for name, route_map_items in route_maps.items():    

%for (seq_no, match_clause, action_clause) in route_map_items:    
route-map ${name} permit ${seq_no} 
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
        % endif      
    %endfor    
!
%endfor            


%endfor
