
hostname ${hostname}
password ${password}
enable password ${enable_password}
                                           

                                
%if snmp:
!
smux peer 1.3.6.1.6.3.1 quagga_zebrad
!
%endif      

%if debug:
!
debug zebra packet recv
debug zebra events
!
%endif               

log file /var/log/zebra/zebra.log
