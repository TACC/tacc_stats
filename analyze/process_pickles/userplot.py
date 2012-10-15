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
import tspl, tspl_utils, masterplot

def do_mp(arg):
  masterplot.master_plot(*arg)

def getuser(file,user,files):
  try:
    ts=tspl.TSPLBase(file,['lnet'],['rx_bytes'])
  except tspl.TSPLException as e:
    return

  if ts.j.acct['owner'] == user:
    files.append(file)

def main():
  parser=argparse.ArgumentParser(description='Deal with a directory of pickle'
                                 ' files nightly')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('-u', help='User',
                      nargs=1, type=str, default=['bbarth'], metavar='username')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  files  = m.list()

  
  partial_getuser=functools.partial(getuser,user=n.u[0],files=files)
  pool.map(partial_getuser,filelist)

  th   = []
  dirs = []
  for f in files:
    th.append(0.)
    dirs.append(n.o[0])

  pool.map(do_mp,zip(files,th,dirs)) # Pool.starmap should exist....

if __name__ == "__main__":
  main()
