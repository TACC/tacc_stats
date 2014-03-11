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

    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    s=[]
    for v in ts:
      s=v
      break

    fig,ax=plt.subplots(2,1,figsize=(8,6),dpi=80)
    ax[0].hold=True
    ax[1].hold=True
    xmin,xmax=[0.,0.]
    xmin1,xmax1=[0.,0.]
    dt=numpy.diff(ts.t)
    for v in ts:
      rate=numpy.array(numpy.divide(numpy.diff(v),dt),dtype=numpy.int64)
      d=numpy.linalg.norm(rate,ord=1)/float(len(rate))
      xmin,xmax=[min(xmin,min(rate)),max(xmax,max(rate))]
      xmin1,xmax1=[min(xmin1,min(rate-d)),max(xmax1,max(rate-d))]
      ax[0].plot(tmid,rate)
      ax[1].plot(tmid,rate-d)

    xmin,xmax=tspl_utils.expand_range(xmin,xmax,.1)
    xmin1,xmax1=tspl_utils.expand_range(xmin1,xmax1,.1)

    ax[0].set_ylim(bottom=xmin,top=xmax)
    ax[1].set_ylim(bottom=xmin1,top=xmax1)

    fname='_'.join(['graph',ts.j.id,ts.k1[0],ts.k2[0],'adjust'+full])
    fig.savefig(fname)
    plt.close()

if __name__ == '__main__':
  main()
  
