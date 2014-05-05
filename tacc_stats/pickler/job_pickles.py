#!/usr/bin/env python
import os,sys

try: 
    sys.path.append(os.getcwd())
    import cfg
except: 
    from tacc_stats.cfg import cfg

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

pickle_prot = pickle.HIGHEST_PROTOCOL

def main(args,processes=1):

    if len(args) < 4:
        USAGE("DIR START_DATE END_DATE PROCESSES");

    prog_name = os.path.basename(args[0])

    pickle_dir = args[1]
    start = getdate(args[2])
    end = getdate(args[3])

    pool = multiprocessing.Pool(processes = processes)
    a=batch_acct.factory(cfg.batch_system, cfg.acct_path, cfg.host_name_ext)
    partial_pickler = functools.partial(job_pickler, pickle_dir = pickle_dir, batch = a)
    pool.imap_unordered(partial_pickler, a.reader(start_time=start,end_time=end,seek=cfg.seek),100)
    pool.close()
    pool.join()


if __name__ == '__main__':
    main(sys.argv)
