## Entries              
% for (root_server, ip) in root_servers:          
.			3600000	IN 	NS	${root_server}.
${root_server}.	3600000 	A	${ip}      
%endfor