% for router, dataList in sorted(conf.items()):   

%for (key,val) in dataList:
${router}[${key}]=${val}
%endfor
%endfor   

# TAP interfaces #

% for router, (int_id, ip) in sorted(tapList.items()):
${router}[${int_id}]=tap,${tapHost},${ip}
%endfor              
