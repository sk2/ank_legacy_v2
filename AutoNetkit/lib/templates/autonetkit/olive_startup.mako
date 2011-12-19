sudo qemu 
    -hda ${router_info.img_image} 
    -hdb ${router_info.iso_image}         
	% for mac in router_info.mac_addresses: 
    -net nic,macaddr=${mac},model=e1000 
	% endfor
    -net vde,sock=${router_info.switch_socket} 
    -enable-kvm 
    -serial telnet:127.0.0.1:${router_info.telnet_port},server,nowait,nodelay 
    -monitor unix:${router_info.monitor_socket},server,nowait 
    -m 512 m  
    -nographic 
    -localtime 
    -name ${router_info.router_name} &