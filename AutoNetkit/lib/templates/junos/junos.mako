system {
    host-name ${hostname};
    root-authentication {
        encrypted-password "$1$NzaHcpA7$5McU2mGx8OG.hWkTbyDtA1"; ## SECRET-DATA
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
	        description "${i['description']}";
            family inet {      
                address ${i['ip']}/${i['prefixlen']};
            }                 
			% if 'net_ent_title' in i:  
			family iso {
				address ${i['net_ent_title']}
			}   
			% elif igp_protocol == 'isis':
			family iso;
			% endif
        }
    }
    %endfor 
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
     
protocols {             
	% if igp_protocol == 'ospf':
	ospf {
	        area 0.0.0.0 {
			% for i in igp_interfaces:
				  % if 'passive' in i:   
				interface ${i['id']}  {
						passive;   
					}
				% else:
				interface ${i['id']};
			  % endif                
			%endfor
	    }
	}                      
	% elif igp_protocol == 'isis':
	isis {               
		level 2 wide-metrics-only;
		level 1 disable;
		% for i in igp_interfaces:   
		% if i['id'].startswith('lo'):
		interface ${i['id']};
		% else:
		interface ${i['id']}  {
			point-to-point;   
			% if 'weight' in i:
			level 2 metric ${i['weight']};
			% endif
		}                        
		% endif
		%endfor    
	}                      
	% endif              
	bgp {                  
		export adverts;
		% for groupname, group_data in bgp_groups.items():   
			group ${groupname} {
				type ${group_data['type']};      
				% for neighbor in group_data['neighbors']: 
				   % if 'peer_as' in neighbor:      
				   neighbor  ${neighbor['id']} {
						peer-as ${neighbor['peer_as']};
				   }
				   % else:          
				   local-address ${router_id};
				   neighbor  ${neighbor['id']};
				   % endif
				% endfor
			}
		% endfor
	}           
}                  

policy-options {
    policy-statement adverts {
        term 1 {
            from protocol [ aggregate direct ];
            then accept;
        }
    }
}