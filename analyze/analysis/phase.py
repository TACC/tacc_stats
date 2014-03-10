#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-f', help='Set full mode', action='store_true')
  parser.add_argument('key1', help='First key', nargs='?',
                      default='amd64_core')
  parser.add_argument('key2', help='Second key', nargs='?',
                      default='SSE_FLOPS')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')

  n=parser.parse_args()
  filelist=tspl_utils.getfilelist(n.filearg)

  for file in filelist:
    try:
      if n.f:
        full='_full'
        ts=tspl.TSPLBase(file,[n.key1],[n.key2])
      else:
        full=''
        ts=tspl.TSPLSum(file,[n.key1],[n.key2])
    except tspl.TSPLException as e:
      continue
    
    if not tspl_utils.checkjob(ts,3600,16): # 1 hour, 16way only
      continue
    elif ts.numhosts < 2: # At least 2 hosts
      print ts.j.id + ': 1 host'
      continue

    print ts.j.id

    fig,ax=plt.subplots(1,1,figsize=(8,6),dpi=80)
    xmin,xmax=[0.,0.]
    for v in ts:
      rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
      xmin,xmax=[min(xmin,min(rate)),max(xmax,max(rate))]
      ax.hold=True
      ax.plot(rate[1:],rate[:-1],'.')
      
    ax.set_ylim(bottom=xmin,top=xmax)
    ax.set_xlim(left=xmin,right=xmax)

    fname='_'.join(['graph',ts.j.id,ts.k1[0],ts.k2[0],'phase'+full])
    fig.savefig(fname)
    plt.close()

if __name__ == '__main__':
  main()
  
