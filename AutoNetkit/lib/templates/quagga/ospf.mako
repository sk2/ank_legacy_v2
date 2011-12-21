!
hostname ${hostname}
password ${password}   
banner motd file /etc/quagga/motd.txt
!
#Setup interfaces         
% for i in interface_list:
interface ${i['id']}
	#Link to ${i['remote_router']}
	ip ospf cost ${i['weight']}        
!
%endfor
##Setup networks             
router ospf    
% for n in network_list:
	network ${n['cidr']} area ${n['area']}
## TODO: check if this is needed  ${n['remote_ip']}
%endfor           
!
##IGP specific options
%if use_igp:
redistribute connected
%endif
##Logfile settings
!
log file ${logfile}
##Debug level
%if use_debug:
debug ospf
%endif 


