#!/usr/bin/env python
import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__),
                             '../lib'))
import sys_conf
sys.path.append(sys_conf.tacc_stats_lib)
from pickler import batch_acct,job_stats
import datetime, subprocess, time
import cPickle as pickle
import multiprocessing, functools

def FATAL(str):
    print >>sys.stderr, "%s: %s" % (__file__, str)
    sys.exit(1)

def USAGE(str):
    print >>sys.stderr, "Usage: %s %s" % (__file__, str)
    sys.exit(1)

def getdate(date_str):
    try:        
        try:
            out = subprocess.check_output(['date', '--date', date_str, '+%s'])
        except:
            out = subprocess.check_output([
                    'date','-j','-f',"""'%Y-%m-%d'""",
                    """'"""+date_str+"""'""",'+%s'])
        return long(out)
    except subprocess.CalledProcessError, e:
        FATAL("Invalid date: `%s'" % (date_str,))

def short_host_name(str):
    return str.split('.')[0]

if len(sys.argv) != 4:
    USAGE("DIR START_DATE END_DATE");

def job_pickler(acct, pickle_dir = '.', batch = None):

    if acct['end_time'] == 0:
        return
    if os.path.exists(os.path.join(pickle_dir, acct['id'])): 
        print acct['id'] + " exists, don't reprocess"
        return

    job = job_stats.from_acct(acct, sys_conf.tacc_stats_home, sys_conf.host_list_dir, batch)
    pickle_path = os.path.join(pickle_dir, job.id)
    pickle_file = open(pickle_path, 'wb')
    pickle.dump(job, pickle_file, pickle_prot)
    pickle_file.close()

pickle_prot = pickle.HIGHEST_PROTOCOL

def main():

    prog_name = os.path.basename(sys.argv[0])

    pickle_dir = sys.argv[1]
    start = getdate(sys.argv[2])
    end = getdate(sys.argv[3])

    pool = multiprocessing.Pool(processes = 1)
    a=batch_acct.factory(sys_conf.batch_system, sys_conf.acct_path, sys_conf.host_name_ext)

    partial_pickler = functools.partial(job_pickler, pickle_dir = pickle_dir, batch = a)
    pool.imap_unordered(partial_pickler, a.reader(start_time=start,end_time=end,seek=sys_conf.seek),100)
    pool.close()
    pool.join()

if __name__ == '__main__': main()
