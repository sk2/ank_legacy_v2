$TTL 1D
@	IN	SOA	lo0.${dns_server}.${domain}.	revdns.${domain} (
		2008080101      ;serial
		8H           	;refresh
		4H           	;retry
		4W         		;expire
		1D          	;negative cache TTL
		)

      	IN      NS       lo0.${dns_server}.${domain}.
                       
## Entries
% for e in entry_list:
${e['reverse']}		PTR	${e['int_id']}.${e['host']}.	     
%endfor