#!/usr/bin/env python
import sys
import analysis_conf
import datetime, glob, job_stats, os, subprocess, time
import operator
import numpy
import scipy, scipy.stats
import argparse
from gen import tspl, tspl_utils, lariat_utils
import math
import multiprocessing, functools, itertools, collections
import cPickle as pickle

def get_data(file,mintime=1.,wayness=range(1,33),ld=None):

  try:
    ts=tspl.TSPLSum(file,['intel_snb_imc', 'intel_snb_imc', 'intel_snb',
                          'intel_snb', 'intel_snb', 'intel_snb','llite',
                          'llite', 'llite', 'llite', 'llite', 'llite',
                          'llite', 'llite', 'llite', 'llite', 'llite',
                          'llite', 'llite', 'llite', 'llite', 'llite',
                          'llite', 'llite', 'llite', 'llite', 'llite',
                          'llite', 'llite', 'llite', 'llite', 'llite',
                          'intel_snb','intel_snb','intel_snb', 'intel_snb', 'intel_snb'],
                    ['CAS_READS', 'CAS_WRITES', 'STALLS',
                     'CLOCKS_UNHALTED_CORE', 'SSE_D_ALL', 'SIMD_D_256',
                     'open','close','mmap','seek','fsync','setattr',
                     'truncate','flock','getattr','statfs','alloc_inode',
                     'setxattr','getxattr',' listxattr',
                     'removexattr', 'inode_permission', 'readdir',
                     'create','lookup',
                     'link','unlink','symlink','mkdir','rmdir','mknod',
                     'rename',
                     'LOAD_OPS_L1_HIT','LOAD_OPS_L2_HIT','LOAD_OPS_LLC_HIT',
                     'LOAD_OPS_ALL','INSTRUCTIONS_RETIRED' ])

  except tspl.TSPLException as e:
    return
  ignore=['gpu','gpudev','vis','visdev','development']  
  if not tspl_utils.checkjob(ts,mintime,wayness,ignore):
    return
  if "FAIL" in ts.status: return
  if "CANCELLED" in ts.status: return

  print ts.j.id
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  
  ld.set_job(ts.j.id,end_epoch=ts.j.end_time,directory=analysis_conf.lariat_path)

  read_rate=numpy.zeros_like(tmid)
  write_rate=numpy.zeros_like(tmid)
  stall_rate=numpy.zeros_like(tmid)
  clock_rate=numpy.zeros_like(tmid)
  avx_rate = numpy.zeros_like(tmid)
  sse_rate = numpy.zeros_like(tmid)
  inst_rate = numpy.zeros_like(tmid)
  meta_rate = numpy.zeros_like(tmid)
  l1_rate = numpy.zeros_like(tmid)
  l2_rate = numpy.zeros_like(tmid)
  l3_rate = numpy.zeros_like(tmid)
  load_rate = numpy.zeros_like(tmid)

  for k in ts.j.hosts.keys():
    read_rate +=numpy.diff(ts.assemble([0],k,0))/numpy.diff(ts.t)
    write_rate+=numpy.diff(ts.assemble([1],k,0))/numpy.diff(ts.t)
    stall_rate+=numpy.diff(ts.assemble([2],k,0))/numpy.diff(ts.t)
    clock_rate+=numpy.diff(ts.assemble([3],k,0))/numpy.diff(ts.t)
    avx_rate  +=numpy.diff(ts.assemble([5],k,0))/numpy.diff(ts.t)
    sse_rate  +=numpy.diff(ts.assemble([4],k,0))/numpy.diff(ts.t)
    inst_rate  +=numpy.diff(ts.assemble([36],k,0))/numpy.diff(ts.t)
    meta_rate +=numpy.diff(ts.assemble(range(5,32),k,0))/numpy.diff(ts.t)
    l1_rate +=numpy.diff(ts.assemble([32],k,0))/numpy.diff(ts.t)
    l2_rate +=numpy.diff(ts.assemble([33],k,0))/numpy.diff(ts.t)
    l3_rate +=numpy.diff(ts.assemble([34],k,0))/numpy.diff(ts.t)
    load_rate += numpy.diff(ts.assemble([35],k,0))/numpy.diff(ts.t)

  read_rate  /= float(ts.numhosts)
  write_rate /= float(ts.numhosts)
  stall_rate /= float(ts.numhosts)
  clock_rate /= float(ts.numhosts)
  avx_rate   /= float(ts.numhosts)
  sse_rate   /= float(ts.numhosts)
  inst_rate   /= float(ts.numhosts)
  meta_rate  /= float(ts.numhosts)
  l1_rate  /= float(ts.numhosts)
  l2_rate  /= float(ts.numhosts)
  l3_rate  /= float(ts.numhosts)
  load_rate /= float(ts.numhosts)

  read_frac=read_rate/(read_rate+write_rate+1)
  stall_frac=stall_rate/clock_rate


  return (ts, ld, tmid,
          read_rate, write_rate, stall_rate, clock_rate, avx_rate, sse_rate, inst_rate,
          meta_rate, l1_rate, l2_rate, l3_rate, load_rate, read_frac, stall_frac)

def do_work(file,mintime,wayness,lariat_dict):
  bad_retval=(None,None,None,None,None,None,None)
  res=get_data(file,mintime,wayness,lariat_dict)
  
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
  parser.add_argument('-o', help='File to output to',
                      nargs=1, type=str, default=[1])
  
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)
  procs  = min(len(filelist),n.p[0])
  output = n.o[0]

  job=pickle.load(open(filelist[0]))
  jid=job.id
  epoch=job.end_time

  ld=lariat_utils.LariatData()
  ld.set_job(jid,end_epoch=epoch,directory=analysis_conf.lariat_path)
  
  if procs < 1:
    print 'Must have at least one file'
    exit(1)
    
  pool = multiprocessing.Pool(processes=procs)

  partial_work=functools.partial(do_work,mintime=3600.,wayness=16,
                                 lariat_dict=ld)

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
  f = open(output,'a')
  for k,v in d.most_common(50):
    print k,v
    f.write(str(k)+" "+str(v)+'\n')
  for (f_stall, mem_rate, cpi, ename, jid, user, su) in results:
    if (f_stall is None) or (not ename in enames):
      continue
    cpec = 1./(1. - f_stall)
    if cpi > 1.0: # and cpec > 2.0:
      print jid, ename, cpi, cpec, user, sus[ename]
      f.write(str(jid)+" "+str(ename)+" "+ str(cpi)+" "+str(cpec)+" "+str(user)+" "+str(sus[ename])+'\n')
  f.close()
if __name__ == '__main__':
  main()

