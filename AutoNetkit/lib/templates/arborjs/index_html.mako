<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html lang="en">
<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <title>AutoNetkit ${title} plot</title>
	<link rel="stylesheet" href="../jsplot/style.css" type="text/css">
  <link rel="stylesheet" href=${css_filename} type="text/css">
</head>
<body>                   
  <h1>AutoNetkit ${title} plot</h1>                                 
  <canvas id="viewport" width="${plot_width}" height="${plot_height}"></canvas>

  <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js"></script>

  <!-- run from the minified library file: -->
  <script src="./jsplot/arbor.js"></script>  
                                              
  <script src="./jsplot/${js_file}"></script>       
  
  <p>
  Plotted at ${timestamp} by <a href="http://packages.python.org/AutoNetkit/">AutoNetkit</a> using <a href="http://arborjs.org/">arbor.js</a>

</body>
</html>
