#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import operator
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
import tspl, tspl_utils, lariat_utils, plot
import math
import multiprocessing, functools, itertools
import cPickle as pickle

def do_work(file,mintime,wayness,lariat_dict):
  retval=(None,None,None,None,None)
  res=plot.get_data(file,mintime,wayness,lariat_dict)
  
  if (res is None):
    return retval

  (ts, ld, tmid,
   read_rate, write_rate, stall_rate, clock_rate, avx_rate, sse_rate, inst_rate,
   meta_rate, l1_rate, l2_rate, l3_rate, load_rate, read_frac, stall_frac) = res

  #  return (scipy.stats.tmean(stall_frac),
  #          scipy.stats.tmean((load_rate - (l1_rate + l2_rate +
  #          l3_rate))/load_rate))

  mean_mem_rate=scipy.stats.tmean(read_rate+write_rate)*64.0
  ename=ld.exc.split('/')[-1]
  ename=tspl_utils.string_shorten(ld.comp_name(ename,ld.equiv_patterns),8)
  if ename=='unknown':
    return retval
  flag=False
  if mean_mem_rate < 75.*1000000000./16.:
    flag=True

  return (scipy.stats.tmean(stall_frac),
          scipy.stats.tmean((load_rate - (l1_rate))/load_rate),
          scipy.stats.tmean(clock_rate/inst_rate),ename,
          flag)
  


def main():

  parser = argparse.ArgumentParser(description='Look for imbalance between'
                                   'hosts for a pair of keys')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])

  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  procs  = min(len(filelist),n.p[0])

  job=pickle.load(open(filelist[0]))
  jid=job.id
  epoch=job.end_time

  ld=lariat_utils.LariatData(jid,end_epoch=epoch,daysback=3,directory=analyze_conf.lariat_path)
  
  if procs < 1:
    print 'Must have at least one file'
    exit(1)
    
  pool = multiprocessing.Pool(processes=procs)

  partial_work=functools.partial(do_work,mintime=3600.,wayness=16,lariat_dict=ld.ld)

  results=pool.map(partial_work,filelist)


  fig1,ax1=plt.subplots(1,1,figsize=(20,8),dpi=80)
  fig2,ax2=plt.subplots(1,1,figsize=(20,8),dpi=80)

  maxx=0.
  for state in [ True, False ]:
    stalls=[]
    misses=[]
    cpis=[]
    enames=[]

    for (s,m,cpi,ename,flag) in results:
      if (s != None and m > 0. and m < 1.0 and flag==state):
        stalls.extend([s])
        misses.extend([m])
        cpis.extend([cpi])
        enames.extend([ename])
        

    markers = itertools.cycle(('o','x','+','^','s','8','p',
                               'h','*','D','<','>','v','d','.'))

    colors  = itertools.cycle(('b','g','r','c','m','k','y'))

    
    fmt={}
    for e in enames:
      if not e in fmt:
        fmt[e]=markers.next()+colors.next()
    
    for (s,c,e) in zip(stalls,cpis,enames):
      #      ax1.plot(numpy.log10(1.-(1.-s)),numpy.log10(c),
      maxx=max(maxx,1./(1.-s))
      ax1.plot((1./(1.-s)),(c),
               marker=fmt[e][0],
               markeredgecolor=fmt[e][1],
                linestyle='', markerfacecolor='None',
               label=e)
      ax1.hold=True
      ax2.plot((1./(1.-s)),(c),
               marker=fmt[e][0],
               markeredgecolor=fmt[e][1],
                linestyle='', markerfacecolor='None',
               label=e)
      ax2.hold=True

    #ax.plot(numpy.log10(stalls),numpy.log10(cpis),fmt)
    #ax.plot(numpy.log10(1.0/(1.0-numpy.array(stalls))),numpy.log10(cpis),fmt)

  ax1.set_xscale('log')
  ax1.set_xlim(left=0.95,right=1.05*maxx)
  ax1.set_yscale('log')
  
  box = ax1.get_position()
  ax1.set_position([box.x0, box.y0, box.width * 0.45, box.height])
  box = ax2.get_position()
  ax2.set_position([box.x0, box.y0, box.width * 0.45, box.height])

  handles=[]
  labels=[]
  for h,l in zip(*ax1.get_legend_handles_labels()):
    if l in labels:
      continue
    else:
      handles.extend([h])
      labels.extend([l])
    
  
  ax1.legend(handles,labels,bbox_to_anchor=(1.05, 1),
            loc=2, borderaxespad=0., numpoints=1,ncol=4)
  ax1.set_xlabel('log(Cycles per Execution Cycle)')
  ax1.set_ylabel('log(CPI)')

  handles=[]
  labels=[]
  for h,l in zip(*ax2.get_legend_handles_labels()):
    if l in labels:
      continue
    else:
      handles.extend([h])
      labels.extend([l])
    
  
  ax2.legend(handles,labels,bbox_to_anchor=(1.05, 1),
            loc=2, borderaxespad=0., numpoints=1,ncol=4)
  ax2.set_xlabel('Cycles per Execution Cycle')
  ax2.set_ylabel('CPI')

  fname='miss_v_stall_log'
  fig1.savefig(fname)

  fname='miss_v_stall'
  fig2.savefig(fname)

  plt.close()

if __name__ == '__main__':
  main()

  
