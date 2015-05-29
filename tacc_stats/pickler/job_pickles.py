#!/usr/bin/env python
from __future__ import print_function

import os,sys
import tacc_stats.cfg as cfg

from tacc_stats.pickler import batch_acct,job_stats
from datetime import datetime,timedelta
import time
import cPickle as pickle
import multiprocessing, functools
import argparse, traceback

def job_pickle(reader_inst, 
               pickle_dir = cfg.pickles_dir, 
               tacc_stats_home = cfg.tacc_stats_home,
               host_list_dir = cfg.host_list_dir,
               acct = None):

    if reader_inst['end_time'] == 0:
        return

    date_dir = os.path.join(pickle_dir,
                            datetime.fromtimestamp(reader_inst['end_time']).strftime('%Y-%m-%d'))
    try: os.makedirs(date_dir)
    except: pass
    
    if os.path.exists(os.path.join(date_dir, reader_inst['id'])): 

        print(reader_inst['id'] + " exists, don't reprocess")
        return
    else:
        print("process Job",reader_inst['id'])

    job = job_stats.from_acct(reader_inst, 
                              tacc_stats_home, 
                              host_list_dir, acct)

    if job:
        with open(os.path.join(date_dir, job.id), 'wb') as pickle_file:
            pickle.dump(job, pickle_file, pickle.HIGHEST_PROTOCOL)

class JobPickles:

    def __init__(self,**kwargs):
        self.processes=kwargs.get('processes',1)
        self.pickles_dir = kwargs.get('pickle_dir',cfg.pickles_dir)
        self.start = kwargs.get('start',None)
        self.end = kwargs.get('end',None)
        if not self.start: self.start = (datetime.now()-timedelta(days=1))
        if not self.end:   self.end   = (datetime.now()+timedelta(days=1))

        self.seek = kwargs.get('seek',cfg.seek)
        self.tacc_stats_home = kwargs.get('tacc_stats_home',cfg.tacc_stats_home)
        self.host_list_dir = kwargs.get('host_list_dir',cfg.host_list_dir)

        self.batch_system = kwargs.get('batch_system',cfg.batch_system)
        self.acct_path = kwargs.get('acct_path',cfg.acct_path)
        self.host_name_ext = kwargs.get('host_name_ext',cfg.host_name_ext)

        print(self.batch_system,self.acct_path,self.host_name_ext)
        self.acct = batch_acct.factory(self.batch_system,
                                       self.acct_path,
                                       self.host_name_ext)

        try:
            self.start = datetime.strptime(self.start,'%Y-%m-%d')
            self.end = datetime.strptime(self.end,'%Y-%m-%d')
        except: pass

        self.start = time.mktime(self.start.date().timetuple())
        self.end = time.mktime(self.end.date().timetuple())
        self.pool = multiprocessing.Pool(processes = self.processes)

        self.partial_pickle = functools.partial(job_pickle, 
                                                pickle_dir = self.pickles_dir, 
                                                tacc_stats_home = self.tacc_stats_home,
                                                host_list_dir = self.host_list_dir,
                                                acct = self.acct)

        print("Use",self.processes,"processes")
        print("Gather node-level data from",self.tacc_stats_home+"/archive/")
        print("Write pickle files to",self.pickles_dir)

    def run(self,jobids = None):
        if jobids:
            print("Pickle following jobs:",jobids)            
            reader = self.acct.find_jobids(jobids)
        else:
            print("Pickle jobs between",
                  datetime.fromtimestamp(self.start),
                  "and",datetime.fromtimestamp(self.end))
            reader = self.acct.reader(start_time=self.start,
                                      end_time=self.end,
                                      seek=self.seek)
        self.pool.map(self.partial_pickle,reader)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run pickler for jobs')

    parser.add_argument('-dir', help='Directory to store data',type=str,default=cfg.pickles_dir)
    parser.add_argument('-start', help='Start date',type=str)
    parser.add_argument('-end', help='End date',type=str)
    parser.add_argument('-p', help='Set number of processes',
                        type=int, default=1)
    parser.add_argument('-jobids', help='Set number of processes',
                        type=str,nargs='+')

    args = parser.parse_args()
    
    pickle_options = { 'processes'       : args.p,
                       'start'           : args.start,
                       'end'             : args.end,
                       'pickle_dir'      : args.dir,
                       }
    pickler = JobPickles(**pickle_options)
    pickler.run(jobids = args.jobids)
