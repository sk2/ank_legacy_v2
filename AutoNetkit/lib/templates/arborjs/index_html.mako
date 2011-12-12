<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html lang="en">
<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
	<title>AutoNetkit plot</title>
	<link rel="stylesheet" href="../jsplot/style.css" type="text/css">
</head>
<body>                   
<h1>AutoNetkit plot</h1>                                 
  % for val in js_files:
  <canvas id="viewport" width="1024" height="768"></canvas>
   % endfor

  <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js"></script>

  <!-- run from the minified library file: -->
  <script src="./jsplot/arbor.js"></script>  
                                              
  % for filename in js_files:
  <script src="./jsplot/${filename}"></script>       
  % endfor
  
  Plotted by <a href="http://packages.python.org/AutoNetkit/">AutoNetkit</a> using <a href="http://arborjs.org/">arbor.js</a>

</body>
</html>
