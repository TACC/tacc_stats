#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import matplotlib
# Set the matplotlib output mode from config if it exists
if not 'matplotlib.pyplot' in sys.modules:
  try:
    matplotlib.use(analyze_conf.matplotlib_output_mode)
  except NameError:
    matplotlib.use('pdf')
    
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils

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
  parser.add_argument('-m', help='Set heatmap mode', action='store_true')
  parser.add_argument('--max', help='Use max instead of mean',
                      action='store_true')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  if n.max:
    func=max
  else:
    func=scipy.stats.tmean

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

    if not tspl_utils.checkjob(ts,3600,16):
      continue

    reduction=[] # place to store reductions via func
    for v in ts:
      rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
      reduction.append(func(rate))
      m=func(reduction)
    if not n.t or m > float(n.t):
      print ts.j.id + ': ' + str(m)
      if n.m:
        fig, fname = heatmap(ts,n,m,full)
      else:
        fig, fname = lineplot(ts,n,m,full)
    else:
      print ts.j.id + ': under threshold, ' + str(m) + ' < ' + n.t

    fig.savefig(fname)      

# Plot key pair vs. time in a a traditional y vs. t line plot--one line per host
# (normal) or one line per data stream (full)
def lineplot(ts,n,m,full):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  fig,ax=plt.subplots(1,1,figsize=(8,6),dpi=80)
  ax.hold=True
  ymin=0. # Wrong in general, but min must be 0. or less
  ymax=0.
  for v in ts:
    rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
    ymin=min(ymin,min(rate))
    ymax=max(ymax,max(rate))
    ax.plot(tmid/3600,rate,'o-')
  ymin,ymax=tspl_utils.expand_range(ymin,ymax,0.1)
  ax.set_ylim(bottom=ymin,top=ymax)
  title=ts.title + ', V: %(V)-8.3g' % {'V' : m}
  plt.suptitle(title)
  ax.set_xlabel('Time (hr)')
  ax.set_ylabel('Total ' + ts.label(ts.k1[0],ts.k2[0]) + '/s')
  fname='_'.join(['graph',ts.j.id,ts.k1[0],ts.k2[0],'vs_t'+full])
  plt.close()

  return fig, fname



# Plot a heat map of the data. X-axis time, Y-axis host (normal) or data stream
# (full). Colorbar for data range.
def heatmap(ts,n,m,full):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
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
  ymin,ymax=tspl_utils.expand_range(ymin,ymax,0.1)

  l=r.shape[0]
  y=numpy.arange(l)
  plt.pcolor(tmid/3600,y,r)
  plt.colorbar()
  plt.clim(ymin,ymax)
  
  title=ts.title + ', V: %(V)-8.3g' % {'V' : m}
  plt.suptitle(title)
  ax.set_xlabel('Time (hr)')
  if n.f:
    ax.set_ylabel('Item')
  else:
    ax.set_ylabel('Host')
  fname='_'.join(['graph',ts.j.id,ts.k1[0],ts.k2[0],'heatmap'+full])
  plt.close()

  return fig, fname



if __name__ == '__main__':
  main()
  
