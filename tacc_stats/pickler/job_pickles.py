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
               archive_dir = cfg.archive_dir,
               host_list_dir = cfg.host_list_dir,
               host_name_ext = cfg.host_name_ext):

    if reader_inst['end_time'] == 0:
        return

    date_dir = os.path.join(pickle_dir,
                            datetime.fromtimestamp(reader_inst['end_time']).strftime('%Y-%m-%d'))

    try: os.makedirs(date_dir)
    except: pass
    
    pickle_file = os.path.join(date_dir, reader_inst['id'])

    validated = False
    if os.path.exists(pickle_file):
        validated = True
        with open(pickle_file) as fd:
            try:
                job = pickle.load(fd)
                for host in job.hosts.values():
                    if not host.marks.has_key('begin %s' % job.id) or not host.marks.has_key('end %s' % job.id):
                        validated = False
                        break
            except: 
                validated = False

    if not validated:
        print(reader_inst['id'] + " is not validated: process")
        with open(pickle_file,'w') as fd:
            job = job_stats.from_acct(reader_inst, archive_dir, 
                                      host_list_dir, host_name_ext)            
            if job: pickle.dump(job, fd, pickle.HIGHEST_PROTOCOL)
    else:
        print(reader_inst['id'] + " is validated: do not process")

class JobPickles:

    def __init__(self,**kwargs):
        self.processes=kwargs.get('processes',1)
        self.pickles_dir = kwargs.get('pickle_dir',cfg.pickles_dir)
        self.start = kwargs.get('start',None)
        self.end = kwargs.get('end',None)
        if not self.start: self.start = (datetime.now()-timedelta(days=1))
        if not self.end:   self.end   = (datetime.now()+timedelta(days=1))

        self.archive_dir = kwargs.get('archive_dir',cfg.archive_dir)
        self.host_list_dir = kwargs.get('host_list_dir',cfg.host_list_dir)

        self.batch_system = kwargs.get('batch_system',cfg.batch_system)
        self.acct_path = kwargs.get('acct_path',cfg.acct_path)
        self.host_name_ext = kwargs.get('host_name_ext',cfg.host_name_ext)

        print(self.batch_system,self.acct_path,self.host_name_ext)
        self.acct = batch_acct.factory(self.batch_system,
                                       self.acct_path)

        try:
            self.start = datetime.strptime(self.start,'%Y-%m-%d')
            self.end = datetime.strptime(self.end,'%Y-%m-%d')
        except: pass

        self.start = time.mktime(self.start.date().timetuple())
        self.end = time.mktime(self.end.date().timetuple())
        self.pool = multiprocessing.Pool(processes = self.processes)

        self.partial_pickle = functools.partial(job_pickle, 
                                                pickle_dir = self.pickles_dir, 
                                                archive_dir = self.archive_dir,
                                                host_list_dir = self.host_list_dir,
                                                host_name_ext = self.host_name_ext)

        print("Use",self.processes,"processes")
        print("Gather node-level data from",self.archive_dir+"/archive/")
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
                                      end_time=self.end)
        #map(self.partial_pickle,reader)
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
