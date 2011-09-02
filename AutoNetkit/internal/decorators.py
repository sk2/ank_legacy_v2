# -*- coding: utf-8 -*-
"""
Decorators for use in AutoNetkit
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['deprecated']

"""
Using decorator examples from http://wiki.python.org/moin/PythonDecoratorLibrary
And stacklevel from http://docs.python.org/library/warnings.html
"""

import warnings
import functools

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""
    
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        message = "Call to deprecated function %(funcname)s." % {
                    'funcname': func.__name__, },
        warnings.warn(message, DeprecationWarning, stacklevel=2)
        
        return func(*args, **kwargs)
    return new_func

