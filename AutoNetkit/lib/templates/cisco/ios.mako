hostname ${hostname}
!
boot-start-marker
boot-end-marker
!
!
aaa new-model
!
!
ip cef
!
% for i in interfaces:
interface ${i['id']}
 description ${i['description']}
 ip address ${i['ip']} ${i['prefixlen']}
 ip router isis
 no shutdown
 duplex auto
 speed auto
!
!
%endfor
!
% if igp_protocol == 'isis':
  % for i in interfaces:
    % if 'net_ent_title' in i:
router isis ${i['net_ent_title']}
    % endif
  % endfor
  % for i in igp_interfaces:
    % if 'passive' in i:
 passive-interface ${i['id']}
    % endif
  % endfor
 redistribute connected
 redistribute static ip
% elif igp_protocol == 'ospf':
router ospf 1
 redistribute connected
 redistribute static
  % for i in igp_interfaces:
 network ${i['id']} 0.0.0.255 area 0
    % if 'passive' in i:
 passive-interface ${i['id']}
    % endif
  % endfor
% endif
ip forward-protocol nd
!
no ip http server
