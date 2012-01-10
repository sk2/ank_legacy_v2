## Entries              
% for root_server in root_servers:          
.			3600000	IN 	NS	DNSroot.
DNSroot.	3600000 	A	${root_server.lo_ip.ip}      
%endfor