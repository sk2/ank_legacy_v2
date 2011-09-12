// description - global definitions.
//
#include "/vmm/bin/common.defs"
config "config" {
display "NULL";                            


% for hostname, host_data in sorted(topology_data.items()):   
vm "${hostname}" {
  // description - hostname of set on VM
  hostname "${hostname}";
  // description Operating system image to load
  ${host_data['image']}
  // description - ge 0/0/0 management interface
  interface "em0" { EXTERNAL;};                           
   % for i in host_data['interfaces']:
  //description ${i['description']}  
  interface "${i['id']}" { bridge "${i['bridge_id']}";};
   % endfor
  // description - configuration file to load on the router
  install "ENV(HOME)/active/configset/${host_data['config']}" "/root/junos.conf";
};
% endfor
    
  PRIVATE_BRIDGES
};
