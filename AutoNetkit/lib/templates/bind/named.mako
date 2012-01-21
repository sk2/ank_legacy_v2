options {
    	allow-query { "any"; };
};   

% if domain:       
//zone for each AS    
zone "${domain}" IN {
	type master;
	file "/etc/bind/db.${domain}";  
	allow-query { "any"; };
};          
% endif
   
% for reverse_identifier in entry_list:
zone "${reverse_identifier}" {
	type master; 
	file "${bind_dir}/db.${reverse_identifier}";        
	allow-query { "any"; };
};	     
%endfor
       
// prime the server with knowledge of the root servers
zone "." {
        type hint;
        file "/etc/bind/db.root";       
	};
                             
%if logging:
logging{
 channel example_log{
	  file "/tmp/named.log" versions 3 size 2m;
	  severity debug 9;
	  print-severity yes;
	  print-time yes;
	  print-category yes;
	};  
 category default{
	 example_log;
	};
};       
%endif      