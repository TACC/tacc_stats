#!/usr/bin/env python
import sys
from tacc_stats.cfg import *
import datetime, glob, os, sge_acct, subprocess, time

prog_name = os.path.basename(sys.argv[0])

def FATAL(str):
    print >>sys.stderr, "%s: %s" % (prog_name, str)
    sys.exit(1)

def USAGE(str):
    print >>sys.stderr, "Usage: %s %s" % (prog_name, str)
    sys.exit(1)

def getdate(date_str):
    try:
        out = subprocess.check_output(['/bin/date', '--date', date_str, '+%s'])
        return long(out)
    except subprocess.CalledProcessError, e:
        FATAL("Invalid date: `%s'" % (date_str,))

host_file_dates = set() # dates we've checked
host_file_path_dict = {} # id to path

def read_host_file_dir(day):
    if day in host_file_dates:
        return
    dir_path = os.path.join(host_list_dir, day.strftime("%Y/%m/%d"))
    for ent in os.listdir(dir_path):
        tup = ent.split('.')
        if len(tup) == 3 and tup[0] == 'prolog_hostfile' and tup[1].isdigit():
            host_file_path_dict[tup[1]] = os.path.join(dir_path, ent)
    host_file_dates.add(day)

def get_host_list_path(acct):
    id = acct['id']
    path = host_file_path_dict.get(id)
    if path:
        return path
    start_date = datetime.date.fromtimestamp(acct['start_time'])
    for days in (0, -1, 1):
        read_host_file_dir(start_date + datetime.timedelta(days))
        path = host_file_path_dict.get(id)
        if path:
            return path
    return None

def get_host_list(acct):
    path = get_host_list_path(acct)
    if not path:
        return []
    try:
        with open(path) as file:
            return [host for line in file for host in line.split()]
    except IOError as (err, str):
        return []

def short_host_name(str):
    return str.split('.')[0]

if len(sys.argv) < 3:
    USAGE("START_DATE END_DATE [HOST]...")

start = getdate(sys.argv[1])
end = getdate(sys.argv[2])
host_set = set(short_host_name(arg) for arg in sys.argv[3:])

def print_acct(acct, host='-'):
    start_time = time.strftime(' %b %d %T ', time.localtime(acct['start_time']))
    end_time = time.strftime(' %b %d %T ', time.localtime(acct['end_time']))
    owner = acct['owner'].ljust(10)
    slots = str(acct['slots']).rjust(5)
    print acct['id'], start_time, end_time, host, owner, slots

# Run though all jobs that ended after start and before end + 3 days.
seek = 600 << 20 # XXX

for acct in sge_acct.reader(open(acct_path),
                            start_time=start,
                            end_time=end + 3 * 86400,
                            seek=seek):
    if acct['end_time'] == 0:
        continue
    if max(acct['start_time'], start) <= min(acct['end_time'], end):
        if host_set:
            for host in get_host_list(acct):
                host = short_host_name(host)
                if host in host_set:
                    print_acct(acct, host)
        else:
            print_acct(acct)
