#!/usr/bin/env python
import analyze_conf
import sys, multiprocessing, itertools
import datetime, glob, job_stats, os
import matplotlib
# Set the matplotlib output mode from config if it exists
if not 'matplotlib.pyplot' in sys.modules:
  try:
    matplotlib.use(analyze_conf.matplotlib_output_mode)
  except NameError:
    matplotlib.use('pdf')
import matplotlib.pyplot as plt
   
import numpy
import scipy
import argparse
import tspl, tspl_utils, lariat_utils

def mem_usage(file):
  try:
    ts=tspl.TSPLSum(file,['mem'],['MemUsed'])
  except tspl.TSPLException as e:
    print e
    return []

  ld=lariat_utils.LariatData(ts.j.id,ts.j.end_time,analyze_conf.lariat_path)
  mem_max=0.
  for host in ts.j.hosts.keys():
    mem_max=max(numpy.max(ts.data[0][host]),mem_max)

  mem_per_core = mem_max/(1024.*1024.*1024.*float(ts.wayness))

  print ts.j.id, ': ', mem_per_core, ts.wayness, ld.threads
  if (int(ts.wayness)*int(ld.threads)) > 16:
    print ts.j.id, 'used more than one thread per core!'

  if (int(ts.wayness)*int(ld.threads)) <= 16 and \
      (int(ts.wayness)*int(ld.threads)) > 0 :
    return [mem_per_core]
  else:
    return []

  

def main():
  
  parser = argparse.ArgumentParser(description='Guesstimate per core usage')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()
  filelist=tspl_utils.getfilelist(n.filearg)

  procs  = min(len(filelist),n.p[0])

  pool = multiprocessing.Pool(processes=procs)

  mpc=pool.map(mem_usage,filelist)

  mpc=list(itertools.chain.from_iterable(mpc))

  print mpc

  hist,bins=numpy.histogram(mpc,30)

  fig,ax=plt.subplots(1,1,figsize=(8,8),dpi=80)
  #  plt.subplots_adjust(hspace=0.35)

  ax.bar(bins[:-1], hist, width = min(numpy.diff(bins)))
  ax.set_xlim(min(bins), max(bins))

  fname='mempercore'

  fig.savefig(fname)
  plt.close()


if __name__ == '__main__':
  main()
