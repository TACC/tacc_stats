#!/usr/bin/env python
import datetime, glob, job_stats, os, sge_acct, subprocess, sys, time
import cPickle as pickle

prog_name = os.path.basename(sys.argv[0])
acct_path = os.getenv('TACC_STATS_ACCT_PATH', '/share/sge6.2/default/common/accounting')
host_list_dir = os.getenv('TACC_STATS_HOST_LIST_DIR', '/share/sge6.2/default/tacc/hostfile_logs')
pickle_prot = pickle.HIGHEST_PROTOCOL

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

if len(sys.argv) != 4:
    USAGE("DIR START_DATE END_DATE");

pickle_dir = sys.argv[1]
start = getdate(sys.argv[2])
end = getdate(sys.argv[3])
seek = 800 << 20 # XXX

# Run though all jobs that ended after start and before end + 3 days.

for acct in sge_acct.reader(open(acct_path),
                            start_time=start,
                            end_time=end,
                            seek=seek):
    if acct['end_time'] == 0:
        continue
    job = job_stats.from_acct(acct)
    pickle_path = os.path.join(pickle_dir, job.id)
    pickle_file = open(pickle_path, 'w')
    pickle.dump(job, pickle_file, pickle_prot)
