% for asn, topology in sorted(physical_topology.items()):
# "physical" topology for AS${asn}
	% for n in sorted(topology['nodes']):
	   net add node ${n}
	% endfor      
	% for (s,t) in sorted(topology['links']):
	   net add link ${s} ${t}
	% endfor                                                     
	
% endfor                       

# Interdomain links
% for (s,t) in sorted(interdomain_links):
   net add link ${s} ${t}
% endfor                    
                       
% for asn, topology in sorted(igp_topology.items()):
# IGP configuration for AS${asn}
net add domain ${asn} igp         
% for n in sorted(topology['nodes']):
   net node ${n} domain ${asn}
% endfor      
% for (s,t, weight) in sorted(topology['links']):
   net link ${s} ${t} igp-weight ${weight}
% endfor                 
net domain ${asn} compute                
                
% endfor                        

% for asn, topology in sorted(ibgp_topology.items()):
# Full mesh of iBGP sessions in AS${asn}
% for n in sorted(topology['routers']):
   bgp add router ${asn} ${n}
% endfor                     
bgp domain ${asn} full-mesh

%endfor        

# eBGP static routes
% for router, peers in sorted(ebgp_topology.items()):              
% for peer_asn, peer in peers:       
net node ${router} route add --oif=${peer} ${peer}/32 1
% endfor
% endfor

# Setup eBGP sessions
% for router, peers in sorted(ebgp_topology.items()):              
bgp router ${router}
% for peer_asn, peer in peers:
	add peer ${peer_asn} ${peer}      	
	peer ${peer} next-hop-self
	peer ${peer} up
% endfor
	exit       
% endfor              
	
# Originate own prefixes
% for router, prefix in sorted(ebgp_prefixes.items()):     
	bgp router ${router} add network ${prefix}
% endfor

sim run               

bgp assert peerings-ok                  
bgp assert reachability-ok