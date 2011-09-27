# -*- coding: utf-8 -*-
"""
Housekeeping
"""
__author__ = "\n".join(['Simon Knight'])
#    Copyright (C) 2009-2011 by Simon Knight, Hung Nguyen

__all__ = ['tidy_archives']

import AutoNetkit.config as config
import glob
import os
import shutil

import logging
LOG = logging.getLogger("ANK")

def tidy_archives():
    """ Moves old archive files into archive directory"""
    LOG.debug("Tidying archives")
    base_dir = config.ank_main_dir
    files_to_archive = glob.glob(os.path.join(base_dir, "*.tar.gz"))

#TODO: make this set in config
    archive_dir = os.path.join(base_dir, "archive")
    if not os.path.exists(archive_dir):
        os.mkdir(archive_dir)

    for fname in files_to_archive:
        file_basename = os.path.basename(fname)
        file_dest = os.path.join(archive_dir, file_basename)
        shutil.move(fname, file_dest)

    return


