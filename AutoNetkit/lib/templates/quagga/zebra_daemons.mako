# daemons file
%if "zebra" in entryList:
zebra=yes
%else:
zebra=no
%endif
##  
%if "bgpd" in entryList:
bgpd=yes
%else:
bgpd=no
%endif
##  
%if "ripd" in entryList:
ripd=yes
%else:
ripd=no
%endif
##  
%if "ospf6d" in entryList:
ospf6d=yes
%else:
ospf6d=no
%endif
##  
%if "ospfd" in entryList:
ospfd=yes
%else:
ospfd=no
%endif
##
%if "ripngd" in entryList:
ripngd=yes
%else:
ripngd=no
%endif