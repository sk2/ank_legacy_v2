$ORIGIN .
$TTL 1D
@       IN      SOA     ROOT-SERVER.  none.nowhere (
                2008080101      ;serial
                8H              ;refresh
                4H              ;retry
                4W                      ;expire
                1D              ;negative cache TTL
                )
                 
@			IN	NS	ROOT-SERVER.
ROOT-SERVER.		IN	A	${server.lo_ip.ip}    

% for (domain, reverse, ip) in sorted(dns_servers, key = lambda x: x[0]):
${domain}.				IN	NS	NS.${domain}.
${reverse}		IN	NS	NS.${domain}.
NS.${domain}.		  	  IN	A 	${ip}

%endfor

