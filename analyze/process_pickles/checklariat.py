#!/usr/bin/env python
# This is an inefficient way to do this, but it maps to existing tools and is
# fast enough for now.
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time, argparse
import numpy
import scipy
import tspl, tspl_utils, lariat_utils
import functools, multiprocessing

def do_check(f,jobs):
  try:
    ts=tspl.TSPLSum(f,['amd64_core'],['SSE_FLOPS'])
  except tspl.TSPLException:
    return

  if not tspl_utils.checkjob(ts,3600,range(1,33)): # 1 hour
    return

  
  ld=lariat_utils.LariatData(ts.j.id,ts.j.end_time,
                             analyze_conf.lariat_path)
  jobs[ts.j.id]=ld.exc
  

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)


  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  jobs   = m.dict()
  check_partial=functools.partial(do_check,jobs=jobs)

  pool.map(check_partial,filelist)
  pool.close()
  pool.join()

    

  total=0.
  hasexec=0.
  for i in jobs.keys():
    total += 1.
    if jobs[i]!='unknown':
      hasexec += 1.
    

  print str(total) + ' ' + str(hasexec) + ' ' + str(hasexec/total)

if __name__ == '__main__':
  main()
