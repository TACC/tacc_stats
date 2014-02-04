#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import operator
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils, lariat_utils, plot
import math
import multiprocessing, functools, itertools, collections
import cPickle as pickle

def do_work(file,mintime,wayness,lariat_dict):
  bad_retval=(None,None,None,None,None,None,None)
  res=plot.get_data(file,mintime,wayness,lariat_dict)
  
  if (res is None):
    return bad_retval

  (ts, ld, tmid,
   read_rate, write_rate, stall_rate, clock_rate, avx_rate, sse_rate, inst_rate,
   meta_rate, l1_rate, l2_rate, l3_rate, load_rate, read_frac, stall_frac) = res

  mean_mem_rate=scipy.stats.tmean(read_rate+write_rate)*64.0
  ename=ld.exc.split('/')[-1]

  if ename=='unknown':
    return bad_retval

  ename=ld.comp_name(ename,ld.equiv_patterns)

  (s, m, cpi) = (scipy.stats.tmean(stall_frac),
                 scipy.stats.tmean((load_rate - (l1_rate))/load_rate),
                 scipy.stats.tmean(clock_rate/inst_rate))

  return (s,m,cpi,ename,ts.j.id,ts.owner,ts.su)

def main():

  parser = argparse.ArgumentParser(description='Look for imbalance between'
                                   'hosts for a pair of keys')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])

  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  procs  = min(len(filelist),n.p[0])

  job=pickle.load(open(filelist[0]))
  jid=job.id
  epoch=job.end_time

  ld=lariat_utils.LariatData(jid,end_epoch=epoch,daysback=3,directory=analyze_conf.lariat_path)
  
  if procs < 1:
    print 'Must have at least one file'
    exit(1)
    
  pool = multiprocessing.Pool(processes=procs)

  partial_work=functools.partial(do_work,mintime=3600.,wayness=16,
                                 lariat_dict=ld.ld)

  results=pool.map(partial_work,filelist)

  print len(results)

  sus={}
  for (f_stall, mem_rate, cpi, ename, jid, user, su) in results:
    if f_stall is None:
      continue
    if ename in sus:
      sus[ename]+=su
    else:
      sus[ename]=su
    
  d=collections.Counter(sus)

  enames=zip(*d.most_common(50))[0]

  for k,v in d.most_common(50):
    print k,v

  for (f_stall, mem_rate, cpi, ename, jid, user, su) in results:
    if (f_stall is None) or (not ename in enames):
      continue
    cpec = 1./(1. - f_stall)
    if cpi > 1.0: # and cpec > 2.0:
      print jid, ename, cpi, cpec, user, sus[ename]
  

if __name__ == '__main__':
  main()

