#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import operator
import matplotlib
# Set the matplotlib output mode from config if it exists
if not 'matplotlib.pyplot' in sys.modules:
  try:
    matplotlib.use(analyze_conf.matplotlib_output_mode)
  except NameError:
    matplotlib.use('pdf')
    
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils, lariat_utils
import functools, multiprocessing
import masterplot
import cPickle as pickle

def do_mp(arg):
  (file,out_dir)=arg
  
  masterplot.mp_wrapper(file,'lines',threshold=False,
                        output_dir=out_dir,prefix='internal_imbalance',
                        mintime=1, wayness=16,
                        header='Within Host Imbalance',wide=True)

  

def compute_imbalance(file,k1,k2,thresh,lariat_dict):
  try:
    ts=tspl.TSPLBase(file,k1,k2)
  except tspl.TSPLException as e:
    return
  except EOFError as e:
    print 'End of file found reading: ' + file
    return

  ignore_qs=['gpu','gpudev','vis','visdev']
  if not tspl_utils.checkjob(ts,3600,16,ignore_qs): # 1 hour, 16way only
    return
  elif ts.numhosts < 2: # At least 2 hosts
    print ts.j.id + ': 1 host'
    return

  if lariat_dict == None:
    ld=lariat_utils.LariatData(ts.j.id,end_epoch=ts.j.end_time,daysback=3,directory=analyze_conf.lariat_path)
  else:
    ld=lariat_utils.LariatData(ts.j.id,olddata=lariat_dict)

  if ld.wayness == -1:
    print 'Unknown wayness: ', ts.j.id
    return
  elif ld.wayness != ts.wayness:
    print 'Lariat and TACC Stats disagree about wayness. Skipping: ', ts.j.id
    return
    
  
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  rng=range(1,len(tmid)) # Throw out first and last
  tmid=tmid[rng]         

  for h in ts.data[0].keys():
    host_data=ts.data[0][h]
    maxval=numpy.zeros(len(rng))
    minval=numpy.ones(len(rng))*1e100
    rate=[]
    for v in host_data:
      rate.append(numpy.diff(v)[rng]/numpy.diff(ts.t)[rng])
      maxval=numpy.maximum(maxval,rate[-1])
      minval=numpy.minimum(minval,rate[-1])

    vals=[]
    mean=[]
    std=[]
    for j in range(len(rng)):
      vals.append([])
      for v in rate:
        vals[j].append(v[j])
      mean.append(scipy.stats.tmean(vals[j]))
      std.append(scipy.stats.tstd(vals[j]))

    ratio=numpy.divide(std,mean)

    var=scipy.stats.tmean(ratio)

    if abs(var) > thresh:
      print ts.j.id + ': ' + str(var)
      return file


def main():

  parser = argparse.ArgumentParser(description='Look for imbalance between'
                                   'hosts for a pair of keys')
  parser.add_argument('threshold', help='Treshold ratio for std dev:mean',
                      nargs='?', default=0.25)
  parser.add_argument('key1', help='First key', nargs='?',
                      default='amd64_core')
  parser.add_argument('key2', help='Second key', nargs='?',
                      default='SSE_FLOPS')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
#  parser.add_argument('-f', help='Set full mode', action='store_true')
#  parser.add_argument('-n', help='Disable plots', action='store_true')
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

  pool=multiprocessing.Pool(processes=procs)

  partial_imbal=functools.partial(compute_imbalance,k1=[n.key1],
                                  k2=[n.key2],thresh=float(n.threshold),
                                  lariat_dict=ld.ld)
  res=pool.map(partial_imbal,filelist)

  pool.close()
  pool.join()

  flagged_jobs=[r for r in res if r]

  print flagged_jobs
  print len(flagged_jobs)

  if len(flagged_jobs) != 0:
    pool = multiprocessing.Pool(processes=min(n.p[0],len(flagged_jobs)))
    pool.map(do_mp,zip(flagged_jobs,[n.o[0] for x in flagged_jobs])) # Pool.starmap should exist....
    pool.close()
    pool.join()
  


if __name__ == '__main__':
  main()
  
