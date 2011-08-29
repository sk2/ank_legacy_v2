!
version 12.3
service timestamps debug datetime msec
service timestamps log datetime msec
no service password-encryption
!
hostname ${hostname}
!
boot-start-marker
boot-end-marker
!
!
memory-size iomem 15
no aaa new-model
ip subnet-zero
ip cef
!
!
!
ip audit po max-events 100
!
!
% for i in interface_list:
interface ${i['id']}
	!Link to ${i['remote_router']}     
	ip address ${i['ip']} ${i['sn']}     
	no shutdown
!
%endfor
router eigrp ${asn}      
	% for subnet, netmask in igp_network_list:
	network ${subnet} ${netmask}
	%endfor
	no auto-summary
!
ip http server      
no ip domain lookup
ip classless
!
!
!         
line con 0
line aux 0
line vty 0 4
!
!
end