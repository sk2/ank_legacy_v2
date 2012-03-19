// description - global definitions.
//
#include "/vmm/bin/common.defs"    

% if image.basedisk:
#define ${image.alias} basedisk "${image.basedisk}" ;         
% endif 
% if private_bridges:
#define LOCAL_BRIDGES \   
## "NOTE: When defining bridges, the last line should not end with a \"  
% for bridge in private_bridges[:-1]:
	bridge "${bridge}" {}; \\
	
% endfor               
	bridge "${private_bridges[-1]}" {};   
%endif

config "config" {
	display "NULL";  
                   
	% for hostname, host_data in sorted(topology_data.items()):   
	vm "${hostname}" {
	  // description - hostname of set on VM
	  hostname "${hostname}";
	  // description Operating system image to load
	  ${host_data['image']}
	  // description management interface
          % if olive_based:
	  interface "em0" { bridge "external"; };
          % else:
	  interface "em0" { EXTERNAL;};                         
          % endif
          % for i in sorted(host_data['interfaces'], key = lambda x: x['id']):
	  //description ${i['description']}  
	  interface "${i['id']}" { bridge "${i['bridge_id']}";};
	   % endfor
	  // description - configuration file to load on the router
	  % if olive_based:
	  install "ENV(HOME)/active/configset/${host_data['config']}" "/root/junos.conf"
	  % else:
	  install "ENV(HOME)/active/configset/${host_data['config']}" "/root/olive.conf"
	  %endif
	};
	% endfor
    
	  PRIVATE_BRIDGES      
};
