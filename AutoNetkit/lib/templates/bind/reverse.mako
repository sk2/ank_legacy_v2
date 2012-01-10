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
% for (reverse, int_id, host) in entry_list:
${reverse}		PTR	${int_id}.${host}.	     
%endfor