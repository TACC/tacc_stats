#!/usr/bin/env python
import argparse,os,sys

try: 
    import tacc_stats.pickler.tests.cfg as cfg
except: 
    import tacc_stats.cfg as cfg

from tacc_stats.pickler import batch_acct,job_stats
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
pickle_prot = pickle.HIGHEST_PROTOCOL
def job_pickler(acct, pickle_dir = '.', batch = None):

    if acct['end_time'] == 0:
        return
    if os.path.exists(os.path.join(pickle_dir, acct['id'])): 
        print acct['id'] + " exists, don't reprocess"
        return
    
    job = job_stats.from_acct(acct, cfg.tacc_stats_home, cfg.host_list_dir, batch)
    pickle_path = os.path.join(pickle_dir, job.id)
    pickle_file = open(pickle_path, 'wb')
    pickle.dump(job, pickle_file, pickle_prot)
    pickle_file.close()

def main(pickle_dir,start,end,processes):
    pool = multiprocessing.Pool(processes = processes)
    a=batch_acct.factory(cfg.batch_system, cfg.acct_path, cfg.host_name_ext)
    partial_pickler = functools.partial(job_pickler, pickle_dir = pickle_dir, batch = a)
    pool.imap_unordered(partial_pickler, a.reader(start_time=getdate(start),end_time=getdate(end),seek=cfg.seek),100)
    pool.close()
    pool.join()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run pickler for jobs')

    parser.add_argument('-dir', help='Directory to store data',
                        nargs=1, type=str)
    parser.add_argument('-start', help='Start date',
                        nargs=1, type=str)
    parser.add_argument('-end', help='End date',
                        nargs=1, type=str)
    parser.add_argument('-p', help='Set number of processes',
                        nargs=1, type=int, default=[1])
    args = parser.parse_args()

    pickle_dir = args.dir[0]
    start = args.start[0]
    end = args.end[0]
    processes = args.p[0]

    main(pickle_dir,start,end,processes)
