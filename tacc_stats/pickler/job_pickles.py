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

"""
def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method,(func_name,obj,cls)
    
def _unpickle_method(func_name,obj,cls):
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass 
        else: break
    return func.__get__(obj,cls)

copy_reg.pickle(types.MethodType,_pickle_method,_unpickle_method)
"""
def unwrap(args):
    print("runing>>>>>>>>>>>")
    try:
        args[0].job_pickle(args[1])
    except:
        print(traceback.format_exc())

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
        #self.reader = self.acct.reader(start_time=self.getdate(self.start),end_time=self.getdate(self.end),seek=self.seek)

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

    def job_pickle(self,reader_inst):

        if reader_inst['end_time'] == 0:
            return
        if os.path.exists(os.path.join(self.pickle_dir, reader_inst['id'])): 
            print(reader_inst['id'] + " exists, don't reprocess")
            return

        job = job_stats.from_acct(reader_inst, self.tacc_stats_home, self.host_list_dir, self.acct)
        with open(os.path.join(self.pickle_dir, job.id), 'wb') as pickle_file:
            pickle.dump(job, pickle_file, self.pickle_prot)

    def run(self):
        pool = multiprocessing.Pool(processes = self.processes)
        reader = self.acct.reader(start_time=self.getdate(self.start),
                                  end_time=self.getdate(self.end),seek=self.seek)
        pool.map(unwrap,zip([self],reader))


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

    pickle_options = { 'processes'       : args.p[0],
                       'start'           : args.start[0],
                       'end'             : args.end[0],
                       'pickle_dir'      : args.dir[0],
                       'batch_system'    : cfg.batch_system,
                       'acct_path'       : cfg.acct_path,
                       'tacc_stats_home' : cfg.tacc_stats_home,
                       'host_list_dir'   : cfg.host_list_dir,
                       'host_name_ext'   : cfg.host_name_ext,
                       'seek'            : cfg.seek
                       }

    pickler = job_pickler(**pickle_options)
    pickler.run()
