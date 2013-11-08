#!/usr/bin/env python

import analyze_conf,sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import numpy
import scipy, scipy.stats
import argparse
import re
import multiprocessing
import functools
import tspl, tspl_utils, lariat_utils, masterplot

def do_mp(arg):
  (file,thresh,out_dir)=arg
  masterplot.mp_wrapper(file,'lines',thresh,out_dir,'highmembw',
                        header='High Memory Bandwdith')

def do_bw(file,thresh,bw):
  bw[file]=has_highbw(file,thresh)

def has_highbw(file,thresh):
  try:
    k1=['intel_snb_imc', 'intel_snb_imc']
    k2=['CAS_READS', 'CAS_WRITES']

    peak = 76.*1.e9
    
    try:
      ts=tspl.TSPLSum(file,k1,k2)
    except tspl.TSPLException as e:
      return

    ignore_qs=['gpu','gpudev','vis','visdev']
    if not tspl_utils.checkjob(ts,3600,range(1,33),ignore_qs): 
      return
    elif ts.numhosts < 2: # At least 2 hosts
      print ts.j.id + ': 1 host'
      return

    gdramrate = numpy.zeros(len(ts.t)-1)
    for h in ts.j.hosts.keys():
      gdramrate += numpy.divide(numpy.diff(64.*ts.assemble([0,1],h,0)),
                                numpy.diff(ts.t))
      
    mdr=scipy.stats.tmean(gdramrate)/ts.numhosts

    print mdr/peak

    #print [ts.j.id,mfr/peak[0],mdr/peak[1],mcr/peak[2]]

    if mdr/peak > thresh:
      return True
    else:
      return False
  except Exception as e:
    import sys
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
    raise e

def main():
  parser = argparse.ArgumentParser(description='Find jobs with high mem'
                                   ' bandwidth')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-t', metavar='threshold',
                      help='Treshold Bandwidth',
                      nargs=1, type=float, default=[0.5])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()
  
  filelist=tspl_utils.getfilelist(n.filearg)

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  bw     = m.dict()
  thresh = n.t[0]
  outdir = n.o[0]
  
  partial_highbw=functools.partial(do_bw,thresh=thresh,bw=bw)

  if len(filelist) != 0:
    pool.map(partial_highbw,filelist)
    pool.close()
    pool.join()

  jobs=[]
  for i in bw.keys():
    if bw[i]:
      jobs.append(i)
  
  
  pool  = multiprocessing.Pool(processes=n.p[0])
  if len(jobs) != 0:
    pool.map(do_mp,zip(jobs,
                       [thresh for x in range(len(jobs))],
                       [outdir for x in range(len(jobs))])) 
    pool.close()
    pool.join()


  print '----------- High BW -----------'
  for i in jobs:
    print i.split('/')[-1]
  
if __name__ == '__main__':
  main()
  
