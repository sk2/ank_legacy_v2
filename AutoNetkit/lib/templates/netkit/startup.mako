% for i in interfaces:
/sbin/ifconfig ${i['int']} ${i['ip']} netmask ${i['netmask']} \
## Include broadcast if set
%if "broadcast" in i:
broadcast ${i['broadcast']} \
%endif
up
%endfor 
\
%if add_localhost:
/sbin/ifconfig lo 127.0.0.1 up
%endif
\
%if del_default_route:
route del default
%endif          
\
% for d in daemons:
/etc/init.d/${d} start
%endfor              
%if set_hostname:
/etc/init.d/hostname.sh 
%endif    
% if default_route:
route add default gw ${default_route}
% endif     
% if use_ssh_key:
chown -R root:root /root     
chmod 755 /root
chmod 755 /root/.ssh
chmod 644 /root/.ssh/authorized_keys
% endif                    
% if chown_bind:
chown root:root /etc/bind/rndc.key
chmod 755 /etc/bind/rndc.key
% endif
