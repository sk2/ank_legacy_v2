## Entries              
% for (root_server, ip) in root_servers:          
.			3600000	IN 	NS	DNSroot.
DNSroot.	3600000 	A	${ip}      
%endfor