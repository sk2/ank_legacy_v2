options {
    	allow-query { "any"; };
};

// delegation zone for the different AS networks
zone "." {
        type master;
        file "/etc/bind/db.root";         
	};          
   
%if logging:
logging {
category "default" { "debug"; };
category "general" { "debug"; };
category "database" { "debug"; };
category "security" { "debug"; };
category "config" { "debug"; };
category "resolver" { "debug"; };
category "xfer-in" { "debug"; };
category "xfer-out" { "debug"; };
category "notify" { "debug"; };
category "client" { "debug"; };
category "unmatched" { "debug"; };
category "network" { "debug"; };
category "update" { "debug"; };
category "queries" { "debug"; };
category "dispatch" { "debug"; };
category "dnssec" { "debug"; };
category "lame-servers" { "debug"; };
channel "debug" {
file "/tmp/nameddbg" versions 2 size 50m;
print-time yes;
print-category yes;
};
};          
%endif
