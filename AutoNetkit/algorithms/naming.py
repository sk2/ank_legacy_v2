# -*- coding: utf-8 -*-
"""
Naming
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['domain', 'fqdn', 'rtr_folder_name', 'hostname']

def domain(network, asn):
    """ Returns domain for a provided network and asn
    Accesses set domain for network, for prodived asn"""
    #TODO: check if can remove this now handle eBGP seperately
    asn = int(asn)
    as_domain = ""
    if asn in network.as_names:
        as_domain = network.as_names[asn]
    else:
        as_domain = "AS{0}".format(asn)

    for illegal_char in [" ", "/", "_", ",", "&amp;", "-"]:
        as_domain = as_domain.replace(illegal_char, "")
    return as_domain

def fqdn(network, node):
    """Returns formatted domain name for
    node r in graph graph."""
    asn = network.asn(node)
    node_domain = domain(network, asn)
    node_label = network.graph.node[node]['label']
    if not node_label:
        # Numeric ID, so unique
        node_label = str(node) 
    name = "{0}.{1}".format(node_label,
                            node_domain)
    # / spaces and underscores are illegal in hostnames
    for illegal_char in [" ", "/", "_", ",", "&amp;", "-"]:
        name = name.replace(illegal_char, "")
    return name

def hostname(network, node):
    """ Returns name with spaces, underscores and other illegal characters
    removed. Useful for Bind/DNS"""
    name = network.graph.node[node]['label']
    if not name:
        # Numeric ID, so unique
        name = str(node) 
    for illegal_char in [" ", "/", "_", ",", "&amp;", "-"]:
        name = name.replace(illegal_char, "")
    return name

def rtr_folder_name(network, node):
    """Returns file system safe name for device, used for folders."""
    asn = network.asn(node)
    asn = int(asn)
    if asn in network.as_names:
        as_domain = network.as_names[asn]
    else:
        as_domain = "AS{0}".format(asn)

    #TODO: come up with shortest unique name, eg Adelaide, Aarnet becomes
    # adl.aar, as want descriptive, but also short name
    label = network.graph.node[node]['label']
    if not label:
        # Numeric ID, so unique
        label = str(node) 
    # Use asn not domain, as domain leads to long filenames
    foldername = "{0}_{1}".format(as_domain, label)
    for illegal_char in [" ", "/", "_", ",", ".", "&amp;", "-", "(", ")"]:
        foldername = foldername.replace(illegal_char, "_")
    # Don't want double _
    while "__" in foldername:
        foldername = foldername.replace("__", "_")
    return foldername
