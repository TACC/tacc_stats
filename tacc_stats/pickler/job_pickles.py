#!/usr/bin/env python
from __future__ import print_function

import os,sys

try: 
    import tacc_stats.pickler.tests.cfg as cfg
except: 
    import tacc_stats.cfg as cfg

from tacc_stats.pickler import batch_acct,job_stats
from datetime import datetime,timedelta
import time
import cPickle as pickle
import multiprocessing, functools
import argparse, traceback

def job_pickle(reader_inst, 
               pickle_dir = '.', 
               tacc_stats_home = cfg.tacc_stats_home,
               host_list_dir = cfg.host_list_dir,
               acct = None,
               pickle_prot = pickle.HIGHEST_PROTOCOL):
    print(reader_inst)
    if reader_inst['end_time'] == 0:
        return

    date_dir = os.path.join(pickle_dir,
                            datetime.fromtimestamp(reader_inst['end_time']).strftime('%Y-%m-%d'))
    try: os.makedirs(date_dir)
    except: pass

    if os.path.exists(os.path.join(date_dir, reader_inst['id'])): 
        print(reader_inst['id'] + " exists, don't reprocess")
        return

    job = job_stats.from_acct(reader_inst, 
                              tacc_stats_home, 
                              host_list_dir, acct)

    with open(os.path.join(date_dir, job.id), 'wb') as pickle_file:
        pickle.dump(job, pickle_file, pickle_prot)

class JobPickles:

    def __init__(self,processes=1,**kwargs):
        self.processes=kwargs.get('processes',1)
        self.start = kwargs.get('start',(datetime.now()-timedelta(days=1)))
        self.end = kwargs.get('end',datetime.now())
        self.pickles_dir = kwargs.get('pickle_dir',cfg.pickles_dir)

        self.seek = kwargs.get('seek',cfg.seek)
        self.batch_system = kwargs.get('batch_system','SLURM')
        self.acct_path = kwargs.get('acct_path',cfg.acct_path)
        self.tacc_stats_home = kwargs.get('tacc_stats_home',cfg.tacc_stats_home)
        self.host_list_dir = kwargs.get('host_list_dir',cfg.host_list_dir)
        self.host_name_ext = kwargs.get('host_name_ext',cfg.host_name_ext)
        self.pickle_prot = pickle.HIGHEST_PROTOCOL
        self.acct = batch_acct.factory(self.batch_system, self.acct_path, self.host_name_ext)

        try:
            self.start = datetime.strptime(self.start,'%Y-%m-%d')
            self.end = datetime.strptime(self.end,'%Y-%m-%d')
        except: pass

        self.start = time.mktime(self.start.timetuple())
        self.end = time.mktime(self.end.timetuple())

    def run(self):
        pool = multiprocessing.Pool(processes = self.processes)
        reader = self.acct.reader(start_time=self.start,
                                  end_time=self.end,
                                  seek=self.seek)

        partial_pickle = functools.partial(job_pickle, 
                                           pickle_dir = self.pickles_dir, 
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
                       }

    pickler = JobPickles(**pickle_options)
    pickler.run()
