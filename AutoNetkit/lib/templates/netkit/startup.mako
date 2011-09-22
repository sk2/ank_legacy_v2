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
