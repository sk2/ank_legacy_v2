$ORIGIN .
$TTL 1D
@       IN      SOA     DNSRoot.  none.nowhere (
                2008080101      ;serial
                8H              ;refresh
                4H              ;retry
                4W                      ;expire
                1D              ;negative cache TTL
                )
                 
@			IN	NS	DNSroot.
DNSroot.		IN	A	${root_servers['ip']}
% for e in dns_servers:

${e['domain']}.				IN	NS	NS.${e['domain']}.
${e['reverse']}.in-addr.arpa	IN	NS	NS.${e['domain']}.
NS.${e['domain']}.			IN	A 	${e['ip']}

%endfor

