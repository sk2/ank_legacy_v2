## Entries
## % for domain, ip in root_servers:

.			3600000	IN 	NS	DNSroot.
DNSroot.	3600000 	A	${root_servers['ip']}

## %endfor
