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
DNSroot.		IN	A	${server.lo_ip.ip}    

% for (domain, reverse, ip) in dns_servers:
${domain}.				IN	NS	NS.${domain}.
${reverse}		IN	NS	NS.${domain}.
NS.${domain}.		  	  IN	A 	${ip}

%endfor

