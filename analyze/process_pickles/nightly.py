#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import numpy
import scipy, scipy.stats
import argparse
import re
import multiprocessing
import functools
import tspl, tspl_utils, imbalance, masterplot, uncorrelated

def do_mp(arg):
  masterplot.master_plot(*arg)

def main():
  parser=argparse.ArgumentParser(description='Deal with a directory of pickle'
                                 ' files nightly')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('threshold', help='Treshold ratio for std dev:mean',
                      nargs='?', default=0.25)
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  ratios = m.dict()
  partial_imbal=functools.partial(imbalance.compute_imbalance,
                                  k1=['amd64_core'],
                                  k2=['SSE_FLOPS'],
                                  threshold=float(n.threshold),
                                  plot_flag=False,full_flag=False,
                                  ratios=ratios)
  pool.map(partial_imbal,filelist)

  badfiles=[]
  th=[]
  for i in ratios.keys():
    v=ratios[i][0]
    if v > float(n.threshold):
      for f in filelist:
        if re.search(i,f):
          badfiles.append(f)
          th.append(v)

  pool.map(do_mp,zip(badfiles,th)) # Pool.starmap should exist....

  bad_users=imbalance.find_top_users(ratios)

  for file in badfiles:
    try:
      ts=tspl.TSPLSum(file,['amd64_core','cpu'],['SSE_FLOPS','user'])
    except tspl.TSPLException as e:
      continue
    uncorrelated.plot_correlation(ts,uncorrelated.pearson(ts),'')
  
if __name__ == "__main__":
  main()
