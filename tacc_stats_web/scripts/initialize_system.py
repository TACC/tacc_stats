#!/usr/bin/env python
"""initialize_system.py

Synopsis
--------
    initialize_system.py [system_name] [archive_path]

Description
-----------
    This script reads the directories in the tacc_stats archive to determine the
    names of nodes.

Environment
-----------
    To access the database, django needs to know the settings module. Use the
    environment variable DJANGO_SETTINGS_MODULE to name the module. The module
    needs to be in the python path, for example assuming this file is in
    /var/www/django_sites.

    $ export PYTHONPATH=/var/www:$PYTHONPATH
    $ export DJANGO_SETTINGS_MODULE='django_sites.settings'
    $ ./initialize_system.py ranger.tacc.utexas.edu /data/archive

"""
from django.conf import settings
import os
import sys

from tacc_stats.models import System, Node

def get_system(system_name):
    """Returns system, adding it if system if not in db."""
    systems = System.objects.filter(name=system_name)
    if len(systems) == 0:
        print "adding system: %s" % system_name
        systems = [System(name=system_name)]
        systems[0].save()
    return systems[0]

def add_node(system, node_name):
    """Adds node, if it doesn't exist"""
    print "adding node: %s" % node_name,
    if system.node_set.filter(name=node_name):
        print "node already exists"
    else:
        system.node_set.create(name=node_name)
        print "node added"

def strip_system_name(system_name, node):
    """Removes the system name from a node"""
    if system_name in node:
        end = node.find(system_name)
        end = end - 1 if node[end-1] == '.' else end
        node = node[:end]
    return node

def create_nodes_from_archive_dir(system_name, archive_path):
    """Grabs directory names in archive and addes the nodes to system"""
    system = get_system(system_name)
    map(lambda node: add_node(system, strip_system_name(system_name,node)),
        filter(os.path.isdir, os.listdir(archive_path)))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "Incorrect usage."
        print "-"*80
        print __doc__
    if '-h' in sys.argv or '--help' in sys.argv:
        print __doc__
    else:
        create_nodes_from_archive_dir(*sys.argv[1:])
