#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import itertools, argparse
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('pdf')
import matplotlib.pyplot as plt
import numpy, scipy, scipy.interpolate
import tspl, tspl_utils
import multiprocessing, functools
import pprint

def get_samples(fn,times):
  try:
    ts=tspl.TSPLSum(fn,['lnet'],['tx_bytes'])
  except tspl.TSPLException as e:
    return

  times.append(sorted(list(ts.j.times)))

def global_interp_lnet_data(ts,samples):
  vals=numpy.zeros(len(samples))
  accum=numpy.zeros(len(ts.j.times))
  for i in range(2):
    for h in ts.data[i].values():
      accum+=h[0]

  if len(ts.j.times)<2:
    return vals
  
  f=scipy.interpolate.interp1d(ts.j.times,accum)

  mint=min(ts.j.times)
  maxt=max(ts.j.times)
  for (s,i) in zip(samples,range(len(samples))):
    if s < mint:
      continue
    elif s > maxt:
      vals[i]+=accum[-1]
    else:
      vals[i]+=f(s)

  return vals

def get_lnet_data_file(fn,samples,histories):
  print fn
  try:
    ts=tspl.TSPLSum(fn,['lnet','lnet'],['tx_bytes','rx_bytes'])
  except tspl.TSPLException as e:
    return

  histories[ts.j.id]=global_interp_lnet_data(ts,samples)

def main():

  parser = argparse.ArgumentParser(description='')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  n=parser.parse_args()
  
  filelist=tspl_utils.getfilelist(n.filearg)

  procs=min(len(filelist),n.p[0])
  pool=multiprocessing.Pool(processes=procs)
  m      = multiprocessing.Manager()
  histories = m.dict()
  times = m.list()

  partial_get_samples=functools.partial(get_samples,times=times)
  pool.map(partial_get_samples,filelist)

  samples=set([])
  for t in times:
    samples=set(sorted(samples.union(set(sorted(t)))))

  samples=numpy.array(sorted(samples))

  partial_glndf=functools.partial(get_lnet_data_file,
                                  samples=samples,histories=histories)

  pool.map(partial_glndf,filelist)
  pool.close()
  pool.join()

  accum=numpy.zeros(len(samples))
  for h in histories.values():
    accum+=h

  fig,ax=plt.subplots(1,1,dpi=80)

  t=numpy.array([float(x) for x in samples])

  t-=t[0]
  ax.plot(t[:-1]/3600.,numpy.diff(accum)/numpy.diff(t)/1e9)

  fig.savefig('bar')
  plt.close()

   
if __name__ == '__main__':
  main()
