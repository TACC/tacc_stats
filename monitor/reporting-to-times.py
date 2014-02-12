#!/usr/bin/env python
import datetime, os, sys, time

# reporting-to-times.py END_TIME_MIN END_TIME_MAX > FILE
# Print "JOBID START_TIME END_TIME HOST..." for each job that ended
# between END_TIME_MIN and END_TIME_MAX.
# reporting-to-times.py $(date -d 'Apr 1 2012' +%s) $(date -d 'Jul 1 2012' +%s) > 2012-03-01

prog_name = os.path.basename(sys.argv[0])

debug = os.getenv('DEBUG', False)
reporting_path = os.getenv('REPORTING', '/share/sge6.2/default/common/reporting')
host_list_dir = '/share/sge6.2/default/tacc/hostfile_logs'
run_time_max = 2 * 86400

def ERROR(str):
    print >>sys.stderr, "%s: %s" % (prog_name, str)

def FATAL(str):
    ERROR(str)
    sys.exit(1)

def USAGE(str):
    print >>sys.stderr, "Usage: %s %s" % (prog_name, str)
    sys.exit(1)

def TRACE(str):
    if debug:
        ERROR(str)

if len(sys.argv) < 3:
    USAGE("END_TIME_MIN END_TIME_MAX")

end_time_min = long(sys.argv[1])
end_time_max = long(sys.argv[2])
now = time.time()

if not (end_time_min < end_time_max):
    FATAL("END_TIME_MIN %d is not less than END_TIME_MAX %d" % (end_time_min, end_time_max))

if not (end_time_max <= now):
    ERROR("END_TIME_MAX %d is in the future, using %d instead" % (end_time_max, now))

time_min = end_time_min - 2 * run_time_max
time_max = end_time_max + run_time_max

def read_host_list_d(d, acc):
    # XXX chdir()s.
    """read a single day's worth of host lists into acc"""
    d_path = os.path.join(host_list_dir, d.strftime("%Y/%m/%d"))
    TRACE("d `%s', d_path `%s'" % (d, d_path))
    try:
        os.chdir(d_path)
    except OSError, exc:
        ERROR("exception %s, cannot chdir to `%s'" % (exc, d_path))
        return
    for ent in os.listdir('.'):
        tup = ent.split('.')
        if not (len(tup) == 3 and tup[0] == 'prolog_hostfile' and tup[1].isdigit()):
            continue
        try:
            jobid = tup[1]
            host_list = [host for line in open(ent) for host in line.split()]
            acc[jobid] = ' '.join(host_list)
        except IOError, exc:
            ERROR("exception %s, cannot read `%s' in `%s'" % (exc, ent, d_path))

def read_host_list_r(t_min, t_max):
    """read all host lists for all days that overlap [t_min, t_max]"""
    acc = {}
    d_prev = datetime.date.fromtimestamp(0)
    for t in range(t_min, t_max, 12 * 3600) + [t_max]:
        d = datetime.date.fromtimestamp(t)
        if d_prev < d:
            read_host_list_d(d, acc)
        d_prev = d
    return acc

job_host_list = read_host_list_r(time_min, time_max)
TRACE("len(job_host_list) %d" % len(job_host_list))

job_start_times = {}

for line in open(reporting_path):
    try:
        if line[0] == '#':
            continue
        
        fields = line.split(':', 8)
        if fields[1] != 'job_log':
            continue
        
        tstamp = long(fields[0])
        action = fields[3]
        jobid = fields[4]
        
        if action == 'sent':
            if time_min <= tstamp and tstamp < end_time_max:
                job_start_times[jobid] = tstamp
        elif action == 'finished':
            end_time = tstamp
            if not (end_time_min <= end_time and end_time < end_time_max):
                continue
            start_time = job_start_times.pop(jobid, None)
            if not start_time:
                TRACE("job `%s' has end_time %d but no start_time\n" % (jobid, end_time))
                continue
            host_list = job_host_list.get(jobid)
            if not host_list:
                ERROR("job `%s' has start_time %d, end_time %d but no host_list" % \
                      (jobid, start_time, end_time))
            print jobid, start_time, end_time, host_list
    
    except Exception, exc:
        ERROR("exception %s, line `%s'" % (exc, line))
