LAB_DESCRIPTION =  ${lab_description}
LAB_VERSION = ${lab_version}
LAB_AUTHOR = ${lab_author}
LAB_WEB = ${lab_web}

% for router, dataList in sorted(conf.items()):   

%for (key,val) in dataList:
${router}[${key}]=${val}
%endfor
%endfor   

# TAP interfaces #

% for router, (int_id, ip) in sorted(tapList.items()):
${router}[${int_id}]=tap,${tapHost},${ip}
%endfor              
