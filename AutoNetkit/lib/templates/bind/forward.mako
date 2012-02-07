##Can check using named-checkzone -d AS1 db.AS1
$ORIGIN ${domain}.
$TTL 1D
@	IN	SOA	ns.${domain}.	info.${domain} (
		2008080101      ;serial
		8H           	;refresh
		4H           	;retry
		4W         		;expire
		1D          	;negative cache TTL
		)
@       IN      NS       ns.${domain}.
        

## Entries               
ns		IN	A	${dns_server_ip}
% for (interface_id, host, ip) in sorted(entry_list, key = lambda x: x[2]):
${interface_id}.${host}	IN	A	${ip}	     
%endfor                      

## CNAME Entries  (note lo:0 is invalid dns name so use lo0 instead )
% for alias, host in sorted(host_cname_list):
${alias}	IN	CNAME	${host}      
%endfor
