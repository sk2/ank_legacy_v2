%for route_map in route_maps:    
policy-statement ${route_map.name} { 
	%for (term_number, match_tuple) in route_map.match_tuples:        
	term ${term_number} {
	    %if len(match_tuple.match_clauses):
	    from  {
	    %for match_clause in match_tuple.match_clauses:
	        % if match_clause.type == "prefix_list":
	        prefix-list ${match_clause.value};
	        % elif match_clause.type == "tag":
	        community [${match_clause.value}];
	        % endif      
	    %endfor
	    }
	    % endif             
	    %if len(match_tuple.action_clauses) or match_tuple.reject: 
	    then {                    
	    %for action_clause in match_tuple.action_clauses:
	        % if action_clause.action == "addTag":
	        community set ${action_clause.value};
	        % elif action_clause.action == "setLP":
	        set local-preference ${action_clause.value};      
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
