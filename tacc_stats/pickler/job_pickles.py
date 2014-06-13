#!/usr/bin/env python
from __future__ import print_function

import os,sys

try: 
    import tacc_stats.pickler.tests.cfg as cfg
except: 
    import tacc_stats.cfg as cfg

from tacc_stats.pickler import batch_acct,job_stats
import datetime, subprocess, time
import cPickle as pickle
import multiprocessing, functools
import argparse, traceback

import copy_reg,types

def FATAL(str):
    print >>sys.stderr, "%s: %s" % (__file__, str)
    sys.exit(1)

def USAGE(str):
    print >>sys.stderr, "Usage: %s %s" % (__file__, str)
    sys.exit(1)

def job_pickle(reader_inst, 
               pickle_dir = '.', 
               tacc_stats_home = cfg.tacc_stats_home,
               host_list_dir = cfg.host_list_dir,
               acct = None,
               pickle_prot = pickle.HIGHEST_PROTOCOL):
    print(reader_inst)
    if reader_inst['end_time'] == 0:
        return
    if os.path.exists(os.path.join(pickle_dir, reader_inst['id'])): 
        print(reader_inst['id'] + " exists, don't reprocess")
        return

    job = job_stats.from_acct(reader_inst, 
                              tacc_stats_home, 
                              host_list_dir, acct)
    with open(os.path.join(pickle_dir, job.id), 'wb') as pickle_file:
        pickle.dump(job, pickle_file, pickle_prot)

class JobPickles:

    def __init__(self,processes=1,**kwargs):
        self.processes=processes
        self.batch_system = kwargs.get('batch_system','SLURM')
        self.pickle_dir = kwargs.get('pickle_dir','.')
        self.acct_path = kwargs.get('acct_path','.')
        self.tacc_stats_home = kwargs.get('tacc_stats_home','.')
        self.host_list_dir = kwargs.get('host_list_dir','.')
        self.host_name_ext = kwargs.get('host_name_ext','')
        self.pickle_prot = pickle.HIGHEST_PROTOCOL
        self.start = kwargs.get('start',None)
        self.end = kwargs.get('end',None)
        self.seek = kwargs.get('seek',0)
        self.acct = batch_acct.factory(self.batch_system, self.acct_path, self.host_name_ext)

    def getdate(self,date_str):
        try:        
            try:
                out = subprocess.Popen(['date', '--date', date_str, '+%s'],stdout=subprocess.PIPE).communicate()[0]
            except:
                out = subprocess.Popen([
                        'date','-j','-f',"""'%Y-%m-%d'""",
                        """'"""+date_str+"""'""",'+%s'],stdout=subprocess.PIPE).communicate()[0]
            return long(out)
        except subprocess.CalledProcessError, e:
            FATAL("Invalid date: `%s'" % (date_str,))

    def run(self):
        pool = multiprocessing.Pool(processes = self.processes)
        reader = self.acct.reader(start_time=self.getdate(self.start),
                                  end_time=self.getdate(self.end),
                                  seek=self.seek)

        partial_pickle = functools.partial(job_pickle, 
                                           pickle_dir = self.pickle_dir, 
                                           tacc_stats_home = self.tacc_stats_home,
                                           host_list_dir = self.host_list_dir,
                                           acct = self.acct,
                                           pickle_prot = self.pickle_prot)
        
        pool.map(partial_pickle,reader)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run pickler for jobs')

    parser.add_argument('-dir', help='Directory to store data',type=str)
    parser.add_argument('-start', help='Start date',type=str)
    parser.add_argument('-end', help='End date',type=str)
    parser.add_argument('-p', help='Set number of processes',
                        type=int, default=1)
    args = parser.parse_args()
    
    pickle_options = { 'processes'       : args.p,
                       'start'           : args.start,
                       'end'             : args.end,
                       'pickle_dir'      : args.dir,
                       'batch_system'    : cfg.batch_system,
                       'acct_path'       : cfg.acct_path,
                       'tacc_stats_home' : cfg.tacc_stats_home,
                       'host_list_dir'   : cfg.host_list_dir,
                       'host_name_ext'   : cfg.host_name_ext,
                       'seek'            : cfg.seek
                       }
    print(pickle_options)
    pickler = JobPickles(**pickle_options)
    pickler.run()
