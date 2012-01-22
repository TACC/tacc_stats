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

    $ export PYTHONPATH=<path_to_tacc_stats_web>:<path_to_tacc_stats_web/apps>:$PYTHONPATH
    $ export DJANGO_SETTINGS_MODULE='tacc_stats_web.settings'

Commands
--------
    build <system_name> <archive_path> :
        Builds the database from job archive
        $ ./build_database.py ranger.tacc.utexas.edu /home/tacc_stats/sample-jobs

    flush:
       Clears the database to be cleaned for next usage

"""
from django.conf import settings
from django.core.management import call_command
import os
import shelve
import sys

sys.path.insert(0, '/home/aterrel/workspace/tacc_stats/monitor')

from tacc_stats.models import Node, System
from tacc_stats.models import Job as tsm_Job

def get_job_shelf(archive_path):
    """Returns the on-disk python job monitor database"""
    return shelve.open(os.path.join(archive_path, 'jobs'))

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
    if len(system.node_set.filter(name=node_name)) == 0:
        system.node_set.create(name=node_name)
        print "added node:", node_name

def strip_system_name(system_name, node):
    """Removes the system name from a node"""
    if system_name in node:
        end = node.find(system_name)
        end = end - 1 if node[end-1] == '.' else end
        node = node[:end]
    return node

def create_nodes_from_job(system, a_job):
    """Grabs directory names in archive and addes the nodes to system"""
    for host in a_job.hosts:
        add_node(system, strip_system_name(system.name, host))

def add_Job(system, a_job):
    if system.job_set.filter(acct_id=int(a_job.id)):
        print "job %s already exists" % a_job.id
        return
    newJob = tsm_Job(acct_id=a_job.id, system=system)
    newJob.owner = a_job.acct['account']
    newJob.begin = a_job.start_time
    newJob.end = a_job.end_time
    newJob.runtime = a_job.end_time - a_job.start_time
    newJob.nr_hosts = len(a_job.hosts)
    newJob.save()
    print "Added job:", a_job.id

def process_job_archive(system_name, archive_path):
    """Given a system name and the job archive, builds the django database"""
    system = get_system(system_name)
    job_shelf = get_job_shelf(archive_path)
    for a_job in job_shelf.values():
        create_nodes_from_job(system, a_job)
        add_Job(system, a_job)

def build_database(system_name, archive_dir, clean=False):
    if clean:
        clean_database()
    call_command('syncdb')
    process_job_archive(system_name, archive_dir)

def clean_database():
    print "cleaning db"
    call_command('flush')

def print_usage_and_exit():
    print "Invalid usage:"
    print __doc__
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage_and_exit()
    elif sys.argv[1] == 'flush':
        clean_database()
    elif sys.argv[1] == 'build':
        if len(sys.argv) != 4:
            print_usage_and_exit()
        build_database(*sys.argv[2:4])
    else:
        print_usage_and_exit()
