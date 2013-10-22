#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import itertools, argparse
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('pdf')
import matplotlib.pyplot as plt
import numpy
import tspl, tspl_utils
import multiprocessing, functools
import pprint

def get_samples(fn,times):
  try:
    ts=tspl.TSPLSum(fn,['lnet'],['tx_bytes'])
  except tspl.TSPLException as e:
    return

  times.append(sorted(list(ts.j.times)))

def get_lnet_data_file(fn,k1,k2,samples,histories):
  try:
    ts=tspl.TSPLSum(fn,k1,k2)
  except tspl.TSPLException as e:
    return

  histories[ts.j.id]=tspl_utils.global_interp_data(ts,samples)

def main():

  parser = argparse.ArgumentParser(description='')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-k1', help='Set first key',
                      nargs='+', type=str, default=['amd64_sock'])
  parser.add_argument('-k2', help='Set second key',
                      nargs='+', type=str, default=['DRAM'])
  parser.add_argument('-f', help='File, directory, or quoted'
                      ' glob pattern', nargs=1, type=str, default=['jobs'])
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.f[0])

  procs=min(len(filelist),n.p[0])
  m      = multiprocessing.Manager()
  histories = m.dict()
  times = m.list()

  print 'Getting samples'
  partial_get_samples=functools.partial(get_samples,times=times)
  pool=multiprocessing.Pool(processes=procs)
  pool.map(partial_get_samples,filelist)

  pool.close()
  pool.join()

  samples=set([])
  for t in times:
    samples=samples.union(t)

  samples=numpy.array(sorted(samples))

#  samples=numpy.array(range(1349067600,1352440800+1,3600))

  print len(samples)

  partial_glndf=functools.partial(get_lnet_data_file,k1=n.k1,k2=n.k2,
                                  samples=samples,histories=histories)

  print 'Getting data'
  pool=multiprocessing.Pool(processes=procs)
  pool.map(partial_glndf,filelist)
  pool.close()
  pool.join()

  accum=numpy.zeros(len(samples))
  for h in histories.values():
    accum+=h

  print 'Plotting'
  fig,ax=plt.subplots(1,1,dpi=80)

  t=numpy.array([float(x) for x in samples])

  t-=t[0]
  ax.plot(t[:-1]/3600.,numpy.diff(accum)/numpy.diff(t))

  fig.savefig('bar')
  plt.close()

   
if __name__ == '__main__':
  main()
