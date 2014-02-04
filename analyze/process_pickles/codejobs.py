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
import tspl, tspl_utils, masterplot, lariat_utils

def do_mp(arg):
  masterplot.master_plot(*arg)

def getcode(file,code,output_dir):
  try:
    ts=tspl.TSPLBase(file,['lnet'],['rx_bytes'])
  except tspl.TSPLException as e:
    return

  ld=lariat_utils.LariatData(ts.j.id,ts.j.end_time,analyze_conf.lariat_path)
  
  ename=ld.exc.split('/')[-1]
  ename=ld.comp_name(ename,ld.equiv_patterns)
  
  if ename == code:
    print ts.j.id, ename, ts.wayness
    masterplot.master_plot(file,output_dir=output_dir,mintime=1,wayness=ts.wayness)

def main():
  parser=argparse.ArgumentParser(description='Find a particular executable '
                                 'name')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('-e', help='Executable',
                      nargs=1, type=str, default=['a.out'], metavar='exec')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()

  partial_getcode=functools.partial(getcode,code=n.e[0],output_dir=n.o[0])
  pool.map(partial_getcode,filelist)
  pool.close()
  pool.join()

if __name__ == "__main__":
  main()
