Topologies
******************

Overview:
+++++++++   
  

                                         
This can then be compiled::

	sk:ank_demo sk2$ autonetkit -f demo.graphml 
	INFO   Loading
	INFO   No asn set for node n0 using default of 1
	INFO   No asn set for node n1 using default of 1
	INFO   No asn set for node n2 using default of 1
	INFO   No asn set for node n3 using default of 1
	INFO   Compiling
	INFO   Configuring Netkit 
                                       

Set the ASN to be 1::         

	sk:ank_demo sk2$ autonetkit -f demo.graphml 
	INFO   Loading
	INFO   Compiling
	INFO   Configuring Netkit       
	



Internet Topology Zoo
______________________________
You can use topologies from the Internet Topology Zoo in AutoNetkit.

Download a file from the zoo dataset at http://topology-zoo.org/dataset.html
The zoo has files available in both graphml and GML formats. These can be seen
in the "Download" column of the dataset table. AutoNetkit uses the
GML format.

Either download the file using your browser, or using a tool such as wget::

    sk:~ sk2$ wget http://topology-zoo.org/files/Aarnet.gml

You can then load this into AutoNetkit using the -f command::

    sk:~ sk2$ autonetkit -f Aarnet.gml 
    INFO   Loading
    INFO   Compiling
    INFO   Configuring IGP
    INFO   Configuring BGP
    INFO   Configuring DNS

And then deploy, plot, etc as per the Quickstart guide.


Quick Conversion Guide
_______________________

You can use the yED graph editor http://www.yworks.com/en/products_yed_about.html to draw topologies that can be used in AutoNetkit.
This is often quicker and easier to verify than drawing them manually.
Download and install yED (it is freely available for Windows, Linux and Mac OS
X).


Draw a network using the circle shape, and lines to represent links. Do not
worry about directionality of arrows --- AutoNetkit treats all links as
bidirectional.


Save the graph in GML format, in File -> Save As, and selecting "GML" as the
file format. yED will warn about using GML format, as it does not store all yED
internal information. This is not a problem for our use.


You will need the Internet Topology Zoo toolset to convert the GML file exported
from yED into a format that can be read by AutoNetkit.

You can install the toolset using easy_install::
    
    easy_install TopZooTools

This will give you access to the yed2zoo script::

    sk:examples sk2$ yed2zoo -f multi_as.gml 
    INFO   Saving to folder: /Users/sk2/Dropbox/PhD/Dev/ANK_v2/examples/zoogml
    INFO   Converting multi_as
    INFO   Wrote to /Users/sk2/Dropbox/PhD/Dev/ANK_v2/examples/zoogml/MultiAs.gml

Example
________
An example Multi AS network was drawn in yED as follows:

.. image:: images/zooconvert.*

Here nodes are named A,B, ... H. They could also be given descriptive names,
such as "Sydney", "Melbourne".


This example is a 3 AS network, as per this diagram:

.. image:: images/multi_as.*

Each router belongs to an AS. They are grouped using the fill color
attribute in yED, and a special "Legend" node. The Legend node specifies the AS
to be used for this fill color. It has the format "Legend: ASx". In the
example it has the fill color of red. This means that any node in the
graph with a fill color of red will belong to AS3. The fill color
can be set in the properties palette of yED:

.. image:: images/zooconvert_palette.*

Once saved in GML format from yED, it can be converted using topzootools. Here
the yED exported GML file is called multi_as.gml::

    sk:examples sk2$ yed2zoo -f multi_as.gml 
    INFO   Saving to folder: /Users/sk2/Dropbox/PhD/Dev/ANK_v2/examples/zoogml
    INFO   Converting multi_as
    INFO   Wrote to /Users/sk2/Dropbox/PhD/Dev/ANK_v2/examples/zoogml/MultiAs.gml

After conversion, the GML looks like:

.. highlight:: yaml

.. literalinclude:: ../../examples/topologies/MultiAs.gml 

.. highlight:: python

And can be loaded in ANK::

    autonetkit -f zoogml/MultiAs.gml --plot
    INFO   Loading
    INFO   Compiling
    INFO   Configuring IGP
    INFO   Configuring BGP
    INFO   Configuring DNS
    INFO   Plotting

AutoNetkit will automatically work out internal IGP routing, as well as iBGP and
eBGP routing.

This can be seen on the below plots:

.. image:: images/multi_as_Network.*
.. image:: images/multi_as_iBGP.*
.. image:: images/multi_as_eBGP.*

