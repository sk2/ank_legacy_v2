system {
    host-name ${hostname};
    root-authentication {
        encrypted-password "$1$NzaHcpA7$5McU2mGx8OG.hWkTbyDtA1"; ## SECRET-DATA
    }
    login {
        user vjunos {
            uid 2000;
            class super-user;
            authentication {
                encrypted-password "$1$0wNMUqBN$89uUNEFiTaFtxobIOP8R10"; ## SECRET-DATA
            }
        }
    }
    services {
        ssh {
            root-login allow;
        }
        telnet;
    }
    syslog {
        user * {
            any emergency;
        }
        file messages {
            any notice;
            authorization info;
        }
        file interactive-commands {
            interactive-commands any;
        }
    }
}

interfaces {
    % for i in interfaces:
    ${i['id']} {
        unit 0 {
            family inet {      
                description "${i['description']}";
                address ${i['ip']}/${i['prefixlen']};
            }
        }
    }
    %endfor 
}             

ospf {
        area 0.0.0.0 {
		% for i in ospf_interfaces:
            interface ${i['id']} { 
			  % if 'passive' in i:
					passive;
			% endif
			}            
		%endfor
    }
}        


routing-options {
    aggregate {
        route 
		%for n in network_list:  
		${n};
		%endfor  
    }
    router-id ${router_id};
    autonomous-system ${asn};
}
  
<%doc>


policy-options {
    policy-statement adverts {
        term 1 {
            from protocol [ aggregate direct ];
            then accept;
        }
    }
}


protocols {
    bgp {
        export adverts;
        % for n in ebgp_neighbor_list:
        group ${n['description']} {
            type external;
            peer-as ${n['remote_as']};
            neighbor ${n['remote_ip']};
        }
        %endfor
        % for n in ibgp_neighbor_list:
        % if n['remote_ip']!=router_id:
        group ${n['description']} {
            type internal;
            neighbor ${n['remote_ip']};
        }
        %endif
        %endfor
    }
                                 
</%doc>
