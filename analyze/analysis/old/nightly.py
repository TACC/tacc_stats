#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import numpy
import scipy, scipy.stats
import argparse
import re
import multiprocessing
import functools
import tspl, tspl_utils, imbalance, masterplot, uncorrelated

def do_mp(arg):
  (file,thresh,out_dir)=arg
  
  masterplot.mp_wrapper(file,'lines',thresh,out_dir,'imbalance',
                        header='Potentially Imbalanced',wide=True)
  masterplot.mp_wrapper(file,'percentile',thresh,out_dir,'imbalance',
                        header='Potentially Imbalanced (Percentiles)',
                        wide=True)

def do_un(arg):
  file,output_dir=arg
  k1={'amd64' : ['amd64_core','cpu'],
      'intel_snb' : [ 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'user'],
      'intel_snb' : ['LOAD_L1D_ALL','user'],}
  try:
    ts=tspl.TSPLSum(file,k1,k2)
  except tspl.TSPLException as e:
    return
  uncorrelated.plot_correlation(ts,uncorrelated.pearson(ts),'',output_dir)

def main():
  parser=argparse.ArgumentParser(description='Deal with a directory of pickle'
                                 ' files nightly')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('threshold', help='Treshold ratio for std dev:mean',
                      nargs='?', default=0.25)
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  ratios = m.dict()
  k1={'amd64' : ['amd64_core'],
      'intel_snb' : [ 'intel_snb'],}
  k2={'amd64' : ['DRAM'],
      'intel_snb' : ['LOAD_L1D_ALL'],}
  partial_imbal=functools.partial(imbalance.compute_imbalance,
                                  k1=k1,
                                  k2=k2,
                                  threshold=float(n.threshold),
                                  plot_flag=False,full_flag=False,
                                  ratios=ratios)
  if len(filelist) != 0:
    pool.map(partial_imbal,filelist)

    pool.close()
    pool.join()

  badfiles=[]
  th=[]
  dirs=[]
  for i in ratios.keys():
    v=ratios[i][0]
    if v > float(n.threshold):
      for f in filelist:
        if re.search(i,f):
          badfiles.append(f)
          th.append(v)
          dirs.append(n.o[0])

  
  if len(badfiles) != 0 or len(th) != 0 or len(dirs) != 0:
    pool = multiprocessing.Pool(processes=n.p[0])
    pool.map(do_mp,zip(badfiles,th,dirs)) # Pool.starmap should exist....
    pool.close()
    pool.join()

  bad_users=imbalance.find_top_users(ratios)

#### Not presently useful
#### pool.map(do_un,zip(badfiles,dirs))

if __name__ == "__main__":
  main()
