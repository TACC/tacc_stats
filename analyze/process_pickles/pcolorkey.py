#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time, traceback
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl

def main():

  parser = argparse.ArgumentParser(description='Plot a key pair for some jobs')
  parser.add_argument('-t', help='Threshold', metavar='thresh')
  parser.add_argument('key1', help='First key', nargs='?',
                      default='amd64_core')
  parser.add_argument('key2', help='Second key', nargs='?',
                      default='SSE_FLOPS')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-f', help='Set full mode', action='store_true')
  parser.add_argument('--max', help='Use max instead of mean',
                      action='store_true')
  n=parser.parse_args(sys.argv[1:])

  filelist=tspl.getfilelist(n.filearg)

  if n.max:
    func=max
  else:
    func=scipy.stats.tmean

  for file in filelist:
    try:
      if n.f:
        full='_full'
        ts=tspl.TSPickleLoaderFull(file,[n.key1],[n.key2])
      else:
        full=''
        ts=tspl.TSPickleLoader(file,[n.key1],[n.key2])
    except tspl.TSPLException as e:
      continue

    if not tspl.checkjob(ts,3600,16):
      continue
    if len(ts.j.hosts.keys()) == 1:
      print ts.j.id + ': 1 host'
      continue

    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    reduction=[] # place to store reductions via func
    for v in ts:
      rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
      reduction.append(func(rate))
      m=func(reduction)
    if not n.t or m > float(n.t):
      print ts.j.id + ': ' + str(m)
      fig,ax=plt.subplots(1,1,figsize=(8,6),dpi=80)
      ymin=0. # Wrong in general, but min must be 0. or less
      ymax=0.
      first=True
      for v in ts:
        rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
        if first:
          r=rate
          first=False
        else:
          r=numpy.vstack((r,rate))

        ymin=min(ymin,min(rate))
        ymax=max(ymax,max(rate))
      ymin,ymax=tspl.expand_range(ymin,ymax,0.1)

      l=len(ts.j.hosts.keys())
      y=numpy.arange(l)
      plt.pcolor(tmid/3600,y,r)
      plt.colorbar()
      plt.clim(ymin,ymax)
      
#      ax.set_ylim(bottom=ymin,top=ymax)
      title=ts.title + ', V: %(V)-8.3g' % {'V' : m}
      ax.set_title(title)
      ax.set_xlabel('Time (hr)')
      ax.set_ylabel('Host')
      fname='_'.join(['graph',ts.j.id,ts.k1[0],ts.k2[0],'heatmap'+full])
      fig.savefig(fname)
      plt.close()
    else:
      print ts.j.id + ': under threshold, ' + str(m) + ' < ' + n.t

if __name__ == '__main__':
  main()
  
