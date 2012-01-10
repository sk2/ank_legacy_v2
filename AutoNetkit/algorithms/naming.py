# -*- coding: utf-8 -*-
"""
Naming
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2012 by Simon Knight, Hung Nguyen

import logging
LOG = logging.getLogger("ANK")

__all__ = ['domain', 'fqdn', 'rtr_folder_name', 'hostname',
        'interface_id', 'tap_interface_id',
        'junos_logical_int_id_ge',
        #move these to seperate module
        'asn', 'label', 'default_route',
        'debug_nodes', 'debug_edges',
        ]


def default_route(node):
    """Returns default router for a server"""
#TODO: check node is a server
    if not node.is_server:
        LOG.debug("Only return default route for servers, %s is a %s" % (node, node.device_type))
        return

    for link in node.network.links(node):
        if link.remote_host.is_router:
            return link.remote_ip

def debug_nodes(graph):
    import pprint
    debug_data = dict( (node.network.fqdn(node), data) for node, data in graph.nodes(data=True))
    pprint.pprint(debug_data)

def debug_edges(graph):
    import pprint
    debug_data = dict( ((src.fqdn, dst.fqdn), data) 
            for src, dst, data in graph.edges(data=True))
    pprint.pprint(debug_data)


#TODO: remove these
def asn(node):
    return node.network.asn(node)

def label(node):
    try:
        return node.network.label(node)
    except AttributeError:
# see if list of nodes
        return [n.network.label(n) for n in node]

def interface_id(platform, olive_qemu_patched=False):
    """Returns appropriate naming function based on target
    olive_qemu_patched means can do int 0->6
    
    """
    if platform == 'netkit':
        return netkit_interface_id
    if platform in ['junosphere', 'junosphere_olive']:
            return junos_int_id_junos
    if platform in ['olive', 'junosphere_olive']:
        if olive_qemu_patched:
            return junos_int_id_olive
        return junos_int_id_olive_patched

    LOG.warn("Unable to map interface id for platform %s" % platform)
#TODO: throw exception

# interface naming
def netkit_interface_id(numeric_id):
    """Returns Netkit (Linux) format interface ID for an AutoNetkit interface ID"""
    return 'eth%s' % numeric_id

def tap_interface_id(network, node):
    """ Returns the next free interface number for the tap interface"""
    return network.get_edge_count(node)/2

def junos_int_id_em(numeric_id):
    """Returns Junos format interface ID for an AutoNetkit interface ID
    eg em1"""
# Junosphere uses em0 for external link
    numeric_id += 1
    return 'em%s' % numeric_id

def junos_int_id_olive_patched(numeric_id):
    return 'em%s' % numeric_id

def junos_int_id_olive(numeric_id):
    """remaps to em0, em1, em3, em4, em5"""
    if numeric_id > 1:
        numeric_id = numeric_id +1
    return 'em%s' % numeric_id

def junos_int_id_junos(numeric_id):
    """Returns Junos format interface ID for an AutoNetkit interface ID
    eg ge-0/0/1"""
# Junosphere uses ge/0/0/0 for external link
    numeric_id += 1
    return 'ge-0/0/%s' % numeric_id

def junos_logical_int_id_ge(int_id):
    """ For routing protocols, refer to logical int id:
    ge-0/0/1 becomes ge-0/0/1.0"""
    return int_id + ".0"

def domain(device):
    """ Returns domain for device"""
    as_name = "AS%s" % device.asn
    domain_elements = [as_name]
    if device.pop:
        domain_elements = [device.pop, as_name]

    domain_label = ".".join(str(e) for e in domain_elements)
    for illegal_char in [" ", "/", "_", ",", "&amp;", "-"]:
        domain_label = domain_label.replace(illegal_char, "")
    return domain_label

def fqdn(network, node):
    """Returns formatted domain name for
    node r in graph graph."""
    name = "%s.%s" % (node.label, domain(node))
    # / spaces and underscores are illegal in hostnames
    for illegal_char in [" ", "/", "_", ",", "&amp;", "-"]:
        name = name.replace(illegal_char, "")
    return name

def hostname(node):
    """ Returns name with spaces, underscores and other illegal characters
    removed. Useful for Bind/DNS"""
    name = node.network.label(node)
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
    label = network.label(node)
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


