#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import math
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
import multiprocessing, functools, cPickle as pickle
import collections, itertools
import tspl, tspl_utils, lariat_utils, my_utils

def compute_ratio(file,lariat_dict=None):
  try:
    ts=tspl.TSPLSum(file,['intel_snb_imc', 'intel_snb_imc',
                          'intel_snb', 'intel_snb', 'intel_snb',
                          'intel_snb', 'intel_snb'],
                    ['CAS_READS', 'CAS_WRITES',
                     'LOAD_L1D_ALL', 'SIMD_D_256', 'SSE_D_ALL',
                     'STALLS', 'CLOCKS_UNHALTED_CORE'])
    
  except tspl.TSPLException as e:
    return

  ignore_qs=['gpu','gpudev','vis','visdev']
  if not tspl_utils.checkjob(ts,3600.,range(1,33),ignore_qs):
    return

  tmid=(ts.t[:-1]+ts.t[1:])/2.0

  if lariat_dict == None:
    ld=lariat_utils.LariatData(ts.j.id,end_epoch=ts.j.end_time,daysback=3,directory=analyze_conf.lariat_path)
  else:
    ld=lariat_utils.LariatData(ts.j.id,olddata=lariat_dict)

  if ld.exc == 'unknown' or ld.wayness != ts.wayness: # try loading older lariat
    ld=lariat_utils.LariatData(ts.j.id,end_epoch=ts.j.end_time,daysback=3,directory=analyze_conf.lariat_path,olddata=ld.ld)
  if ld.exc == 'unknown' or ld.wayness != ts.wayness: # Still nothing; return
    return

  read_rate  = numpy.zeros_like(tmid)
  write_rate = numpy.zeros_like(tmid)
  l1_rate    = numpy.zeros_like(tmid)
  avx_rate   = numpy.zeros_like(tmid)
  sse_rate   = numpy.zeros_like(tmid)
  stall_rate = numpy.zeros_like(tmid)
  clock_rate = numpy.zeros_like(tmid)


  for host in ts.j.hosts.keys():
    read_rate  += numpy.diff(ts.assemble([0],host,0))/numpy.diff(ts.t)
    write_rate += numpy.diff(ts.assemble([1],host,0))/numpy.diff(ts.t)
    l1_rate    += numpy.diff(ts.assemble([2],host,0))/numpy.diff(ts.t)
    avx_rate   += numpy.diff(ts.assemble([3],host,0))/numpy.diff(ts.t)
    sse_rate   += numpy.diff(ts.assemble([4],host,0))/numpy.diff(ts.t)
    stall_rate += numpy.diff(ts.assemble([5],host,0))/numpy.diff(ts.t)
    clock_rate += numpy.diff(ts.assemble([6],host,0))/numpy.diff(ts.t)

  if float(ts.numhosts*int(ts.wayness)*int(ld.threads)) == 0:
    print 'No tasks in', ts.j.id, ' skipping'
    return

  read_rate  /= float(ts.numhosts*int(ts.wayness)*int(ld.threads))
  write_rate /= float(ts.numhosts*int(ts.wayness)*int(ld.threads))
  l1_rate    /= float(ts.numhosts*int(ts.wayness)*int(ld.threads))
  avx_rate   /= float(ts.numhosts*int(ts.wayness)*int(ld.threads))
  sse_rate   /= float(ts.numhosts*int(ts.wayness)*int(ld.threads))
  stall_rate /= float(ts.numhosts*int(ts.wayness)*int(ld.threads))
  clock_rate /= float(ts.numhosts*int(ts.wayness)*int(ld.threads))
    

  try:
    data_ratio  = (read_rate+write_rate)/l1_rate
  except RuntimeWarning:
    print 'Division by zero, skipping:', ts.j.id
    return
  flops       = avx_rate+sse_rate
  try:
    flops_ratio = (flops-numpy.min(flops))/(numpy.max(flops)-numpy.min(flops))
  except RuntimeWarning:
    print 'Division by zero, skipping:', ts.j.id
    return
  try:
    stall_ratio = stall_rate/clock_rate
  except RuntimeWarning:
    print 'Division by zero, skipping:', ts.j.id
    return


  mean_data_ratio=numpy.mean(data_ratio)
  mean_stall_ratio=numpy.mean(stall_ratio)
  mean_mem_rate=numpy.mean(read_rate + write_rate)*64.0
  if mean_stall_ratio > 1.:
    return
  elif mean_mem_rate > 75.*1000000000./16.:
    return

  ename=ld.exc.split('/')[-1]
  ename=ld.comp_name(ename,ld.equiv_patterns)
##  if mean_mem_rate > 2e9: # Put a print in here and investigate bad jobs
##    return
  return (ts.j.id, ts.su, ename, mean_data_ratio, mean_stall_ratio, mean_mem_rate )

def main():
  mem_rate_thresh = 0.5*75*1000000000/16
  stall_thresh    = 0.5
  parser = argparse.ArgumentParser(description='Correlations')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-n', help='Set number of executables to catalog',
                      nargs=1, type=int, default=[15])
  parser.add_argument('-s', help='Use SUs instead of job counts',
                      action='store_true')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  job=pickle.load(open(filelist[0]))
  jid=job.id
  epoch=job.end_time

  ld=lariat_utils.LariatData(jid,end_epoch=epoch,daysback=3,directory=analyze_conf.lariat_path)
  
  if n.p[0] < 1:
    print 'Must have at least one file'
    exit(1)

  partial_compute=functools.partial(compute_ratio,lariat_dict=ld.ld)

  pool   = multiprocessing.Pool(processes=n.p[0])

  res=pool.map(partial_compute,filelist)
  pool.close()
  pool.join()

  mdr={}
  msr={}
  mmr={}
  sus={}
  for tup in res:
    try:
      (jobid,su,ename,mean_data_ratio,mean_stall_ratio,mean_mem_rate) = tup
    except TypeError as e:
      continue
    if ename in mdr:
      mdr[ename]=numpy.append(mdr[ename],numpy.array([mean_data_ratio]))
      msr[ename]=numpy.append(msr[ename],numpy.array([mean_stall_ratio]))
      mmr[ename]=numpy.append(mmr[ename],numpy.array([mean_mem_rate]))
      sus[ename]+=su
    else:
      mdr[ename]=numpy.array([mean_data_ratio])
      msr[ename]=numpy.array([mean_stall_ratio])
      mmr[ename]=numpy.array([mean_mem_rate])
      sus[ename]=su
    if (mean_mem_rate <= mem_rate_thresh) and \
       (mean_stall_ratio > stall_thresh) :
      print ename, jobid, mean_mem_rate/1000000000, mean_stall_ratio
    

  # Find top codes by SUs
  top_count={}
  for k in mdr.keys():
    if n.s:
      top_count[k]=sus[k] # by sus
    else:
      top_count[k]=len(mdr[k]) # by count

  d = collections.Counter(top_count)

  mdr2={}
  msr2={}
  mmr2={}
  for k,v in d.most_common(n.n[0]):
    print k,v
    mdr2[k]=numpy.log10(mdr[k])
    msr2[k]=msr[k]
    mmr2[k]=numpy.log10(mmr[k])
  
#  for k in mdr.keys():
#    if len(mdr[k]) < 5:
#      continue
#    mdr2[k]=mdr[k]

  x=[top_count[k] for k in mdr2.keys()]

  l=len(mdr2.keys())
  y=numpy.linspace(0.10,0.95,l)
  widths=numpy.interp(x,numpy.linspace(5.0,float(max(x)),l),y)
  

  fig,ax=plt.subplots(1,1,figsize=(8,8),dpi=80)
  plt.subplots_adjust(hspace=0.35,bottom=0.25)


  ax.boxplot(mdr2.values(),widths=widths)
  xtickNames = plt.setp(ax,xticklabels=mdr2.keys())
  plt.setp(xtickNames, rotation=45, fontsize=8)
  ax.set_ylabel(r'log(DRAM BW/L1 Fill Rate)')
  
  fname='box_mdr'
  fig.savefig(fname)
  plt.close()

  markers = itertools.cycle(('o','x','+','^','s','8','p',
                             'h','*','D','<','>','v','d','.'))

  colors  = itertools.cycle(('b','g','r','c','m','k','y'))

  fig,ax=plt.subplots(1,1,figsize=(10,8),dpi=80)

  for k in mdr2.keys():
    ax.plot(mdr2[k],msr2[k],marker=markers.next(),
            markeredgecolor=colors.next(),
            linestyle='', markerfacecolor='None')
    ax.hold=True

  box = ax.get_position()
  ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])
  ax.legend(mdr2.keys(),bbox_to_anchor=(1.05, 1),
            loc=2, borderaxespad=0., numpoints=1)

  ax.set_xlabel('log(DRAM BW/L1 Fill Rate)')
  ax.set_ylabel('Stall Fraction')

  fname='msr_v_mdr'
  fig.savefig(fname)
  plt.close()

  markers = itertools.cycle(('o','x','+','^','s','8','p',
                             'h','*','D','<','>','v','d','.'))

  colors  = itertools.cycle(('b','g','r','c','m','k','y'))

  fig,ax=plt.subplots(1,1,figsize=(10,8),dpi=80)

  for k in mdr2.keys():
    ax.plot(mmr2[k],msr2[k],marker=markers.next(),
            markeredgecolor=colors.next(),
            linestyle='', markerfacecolor='None')
    ax.hold=True


  ax.plot(numpy.log10([mem_rate_thresh, mem_rate_thresh]),
          [0.95*min(numpy.concatenate(msr2.values())),
           1.05*max(numpy.concatenate(msr2.values()))],
          'r--')

  print [min(numpy.concatenate(mmr2.values())), max(numpy.concatenate(mmr2.values()))], [stall_thresh, stall_thresh], 'r--'
  ax.plot([min(numpy.concatenate(mmr2.values())),
           max(numpy.concatenate(mmr2.values()))],
          [stall_thresh, stall_thresh],
          'r--')
  

  box = ax.get_position()
  ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])
  ax.legend(mdr2.keys(),bbox_to_anchor=(1.05, 1),
            loc=2, borderaxespad=0., numpoints=1)

  ax.set_xlabel('log(DRAM BW)')
  ax.set_ylabel('Stall Fraction')

  fname='msr_v_mem'
  fig.savefig(fname)
  plt.close()

if __name__ == '__main__':
  main()
