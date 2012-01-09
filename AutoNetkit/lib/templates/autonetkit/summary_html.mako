<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html lang="en">
<head>
  <link rel="stylesheet" href=${css_filename} type="text/css">
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
	<title>AutoNetkit Network Summary</title>
</head>
<body>                   
<h1>AutoNetkit Network Summary</h1>        

<h2>Plots</h2>
<ul>
  <li><a href="plot.html">Physical Graph</a></li>     
  <li><a href="ip.html">IP Graph</a></li>
  <li><a href="ibgp.html">iBGP Graph</a></li>
  <li><a href="ebgp.html">eBGP Graph</a></li>
  <li><a href="dns.html">DNS Graph</a></li>
</ul>

<h2>Network Statistics</h2>
	<table>
		<tr> <th>Total Routers:</th> <td>${network_stats['node_count']}</td> </tr>     
		<tr> <th>Total Links:</th> <td>${network_stats['edge_count']}</
			td> </tr>       
		<tr> <th>Autonomous Systems:</th> <td>${network_stats['as_count']}</td> </tr>                         
	</table>

% for asn, as_data in as_stats.items():
<h2>AS${asn}</h2>
	<table>
		<tr> <th>Router</th> <th>Loopback</th> </tr>     
    %for router, loopback in as_data['loopbacks']:
    <tr> <td>${router}</td> <td>${loopback}</ td> </tr>       
      % endfor
  </table>

  % for node, node_data in sorted(as_data['node_list'].items()):
  <h3>${node}</h3>
  ${len(node_data['interface_list'])} interfaces
	<table>
    <tr> <th>Neighbour</th> <th>Subnet</th> </tr>     
    %for neigh, subnet in node_data['interface_list']:
    <tr> <td>${neigh}</td> <td>${subnet}</ td> </tr>       
      % endfor
  </table>
  
  <h4>iBGP peers</h4>
  <table>
    <tr> <th>Neighbour</th> <th>Loopback</th> </tr>     
    %for neigh, subnet in node_data['ibgp_list']:
    <tr> <td>${neigh}</td> <td>${subnet}</ td> </tr>       
      % endfor
    </table>

  <h4>eBGP peers</h4>
  <table>
  <table>
    <tr> <th>Neighbour</th> <th>Loopback</th> </tr>     
    %for neigh, subnet in node_data['ebgp_list']:
    <tr> <td>${neigh}</td> <td>${subnet}</ td> </tr>       
      % endfor
  </table>
  % endfor

  <hr>

%endfor
  
<p>
Generated at ${timestamp} by <a href="http://packages.python.org/AutoNetkit/">AutoNetkit</a>
</body>
</html>
