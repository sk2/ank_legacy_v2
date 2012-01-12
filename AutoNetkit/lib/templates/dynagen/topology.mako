autostart = True
[hypervisor_server]
    workingdir = ${working_dir}
    udp = 10000
    [[${hypervisor_port}]]
        image = ${image}
        ghostios = True
        chassis = ${chassis}        
% for id, data in (all_router_info.items()):           
      [[ROUTER ${data['hostname']}]]                                      
			model  = ${data['model']}          
			console =  ${data['console']}           
			cnfg = ${data['cnfg']}           
			%if 'slot1' in data:
			slot1 = ${data['slot1']}     
			%endif
         % for int_id, dst_int_id, dst_label in data['links']:  
			${int_id} = ${dst_label} ${dst_int_id}          
         %endfor              
%endfor              
[GNS3-DATA]
    configs = configs
