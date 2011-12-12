%for name, route_map_items in route_maps.items():    

policy-statement ${name} { 
%for (match_clause, action_clause) in route_map_items:    
    %if len(match_clause):
    from  {
    %for (match_type, comparison, match_value) in match_clause:
        % if match_type == "prefix_list":
        prefix-list ${match_value};
        % elif match_type == "tag":
        community [${match_value}];
        % endif      
    %endfor
    }
    % endif             
    %if len(action_clause): 
    then {
    %for (action_type, action_value) in action_clause:       
        % if action_type == "addTag":
        community set ${action_value};
        % elif action_type == "setLP":
        set local-preference ${action_value};      
        % elif action_type == "setNextHop":
        next-hop ${action_value};  
        % elif action_type == "removeTag":
        community delete ${action_value};
        % endif     
    %endfor    
    } 
    % endif 
%endfor            
}


%endfor
