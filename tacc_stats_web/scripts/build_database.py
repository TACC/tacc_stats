#!/usr/bin/env python
"""build_database.py

Synopsis
--------
    build_database.py [system_name] [archive_path]

Description
-----------
    Builds the database from archive directory

Environment
-----------
    To access the database, django needs to know the settings module. Use the
    environment variable DJANGO_SETTINGS_MODULE to name the module. The module
    needs to be in the python path, for example assuming this file is in
    /var/www/django_sites.

    $ export PYTHONPATH=/var/www:$PYTHONPATH
    $ export DJANGO_SETTINGS_MODULE='django_sites.settings'
    $ ./build_database.py ranger.tacc.utexas.edu /data/archive

"""
from django.conf import settings
from django.core.management import call_command
import os
import sys

from initialize_system import create_nodes_from_archive_dir

def build_database(system_name, archive_dir):
    call_command('syncdb')
    initialize_system(system_name, archive_dir)

def clean_database():
    call_command('flush')

if __name__ == "__main__":
    build_database(*sys.argv[1:])
