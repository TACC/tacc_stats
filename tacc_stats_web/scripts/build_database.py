#!/usr/bin/env python
"""build_database.py

Synopsis
--------
    build_database.py <command> [command args]

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
from django.db.utils import DatabaseError
from django.db import transaction
import os
import shelve
import sys

sys.path.insert(0, '/home/aterrel/workspace/tacc_stats/monitor')

from tacc_stats.models import Node, System, User
from tacc_stats.models import Job as tsm_Job
import job


def get_job_shelf(archive_path):
    """Returns the on-disk python job monitor database"""
    return shelve.open(os.path.join(archive_path, 'jobs'))

def get_system(system_name):
    """Returns system, adding it if system if not in db."""
    systems = System.objects.filter(name=system_name)
    if len(systems) == 0:
        print "Adding system: %s" % system_name
        system = System(name=system_name)
        system.save()
    else:
        system = systems[0]
    return system

def get_node(system, node_name):
    """Returns node, if it doesn't exist it is created"""
    node_name = strip_system_name(system.name, node_name)
    nodes = system.node_set.filter(name=node_name)
    if len(nodes) == 0:
        print "Adding node: %s" % node_name
        node = system.node_set.create(name=node_name)
    else:
        node = nodes[0]
    return node

def get_user(user_name, system):
    """Returns the user cooresponding to the user_name, if it doesn't exist it is created"""
    users = User.objects.filter(user_name=user_name)
    if len(users) == 0:
        print "Adding user:", user_name
        user = User(user_name = user_name)
        user.save()
    else:
        user = users[0]
    user.systems.add(system)
    return user

def strip_system_name(system_name, node):
    """Removes the system name from a node"""
    if system_name in node:
        end = node.find(system_name)
        end = end - 1 if node[end-1] == '.' else end
        node = node[:end]
    return node

def add_Job(system, a_job):
    if system.job_set.filter(acct_id=int(a_job.id)):
        print "Job %s already exists" % a_job.id
        return
    owner = get_user(a_job.acct['account'], system)
    #nr_bad_hosts = len(filter(lambda h: len(h.times) < 2,
    #                          a_job.hosts.values()))
    job_dict = {
        'system': system,
        'acct_id': a_job.id,
        'owner': owner,
        'queue': a_job.acct['queue'],
        'queue_wait_time': a_job.start_time - a_job.acct['submission_time'],
        'begin': a_job.start_time,
        'end': a_job.end_time,
        #'nr_bad_hots': nr_bad_hosts,
        'nr_slots': a_job.acct['slots'],
        'pe': a_job.acct['granted_pe'],
        'failed': a_job.acct['failed'],
        'exit_status': a_job.acct['exit_status'],
    }
    job_dict.update(job.JobAggregator(a_job).stats)
    #newJob.nr_hosts = len(a_job.hosts)
    try:
        newJob = tsm_Job(**job_dict)
        newJob.save()
    except DatabaseError:
        print "Error on job,", a_job.id
        transaction.rollback()
        return
    hosts = map(lambda node: get_node(system, node), a_job.hosts.keys())
    newJob.hosts = hosts

    print "Added job:", a_job.id

def process_job_archive(system_name, archive_path):
    """Given a system name and the job archive, builds the django database"""
    system = get_system(system_name)
    job_shelf = get_job_shelf(archive_path)
    for a_job in job_shelf.values():
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
