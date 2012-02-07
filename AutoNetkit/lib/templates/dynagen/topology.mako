autostart = True
[${hypervisor_server}]
    workingdir = ${working_dir}
    udp = 10000
    [[${hypervisor_port}]]
        image = ${image}
        ghostios = True
        chassis = ${chassis}   
		%for option, value in sorted(options.items()):
		${option} = ${value}
		%endfor  
   		%for slot, wic in sorted(slots.items(), key = lambda x: x[0]):
		${slot} = ${wic}
		%endfor           
% for id, data in sorted(all_router_info.items(), key = lambda x: x[1]['hostname']):           
      [[ROUTER ${data['hostname']}]]     
			console = ${data['console']}           
			cnfg = ${data['cnfg']}           
         % for int_id, dst_int_id, dst_label in sorted(data['links'], key = lambda x: x[0]):  
			${int_id} = ${dst_label} ${dst_int_id}          
         %endfor              
%endfor              
[GNS3-DATA]
    configs = configs
