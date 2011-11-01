Topologies
******************

Overview:
+++++++++   

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
