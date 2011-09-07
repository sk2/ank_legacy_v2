##Can check using named-checkzone -d nap db.nap
$ORIGIN ${domain}.
$TTL 1D
@	IN	SOA	${domain}.	info.${domain} (
		2008080101      ;serial
		8H           	;refresh
		4H           	;retry
		4W         		;expire
		1D          	;negative cache TTL
		)
@       IN      NS       lo0.${dns_server}
        

## Entries
% for e in entry_list:
${e['int_id']}.${e['host']}	IN	A	${e['int_ip']}	     
%endfor    

## CNAME Entries  (note lo:0 is invalid dns name so use lo0 instead )
% for alias, host in host_cname_list:
${alias}	IN	CNAME	${host}      
%endfor