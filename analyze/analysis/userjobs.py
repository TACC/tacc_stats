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
import tspl, tspl_utils, masterplot

def getuser(file,user,output_dir):
  try:
    ts=tspl.TSPLBase(file,['lnet'],['rx_bytes'])
  except tspl.TSPLException as e:
    return

  if ts.owner == user:
    masterplot.mp_wrapper(file,output_dir=output_dir,wide=True)

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

  partial_getuser=functools.partial(getuser,user=n.u[0],output_dir=n.o[0])
  pool.map(partial_getuser,filelist)
  pool.close()
  pool.join()

if __name__ == "__main__":
  main()
