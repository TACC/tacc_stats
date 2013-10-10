#!/usr/bin/env python

execfile('./analyze.conf') # configuration parameters are stored here

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import operator
import matplotlib
# Set the matplotlib output mode from config if it exists
if not 'matplotlib.pyplot' in sys.modules:
  try:
    matplotlib.use(matplotlib_output_mode)
  except NameError:
    matplotlib.use('pdf')
    
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils, lariat_utils
import math

def getlimits(vals):
    ymin=0.
    ymax=0.
    ymin=min(ymin,min(vals))
    ymax=max(ymin,max(vals))
    return (ymin,ymax)


def main():

  parser = argparse.ArgumentParser(description='Look for imbalance between'
                                   'hosts for a pair of keys')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')

  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  for file in filelist:
    try:
      ts=tspl.TSPLSum(file,['intel_snb_imc', 'intel_snb_imc', 'intel_snb',
                            'intel_snb', 'intel_snb', 'intel_snb','llite',
                            'llite', 'llite', 'llite', 'llite', 'llite',
                            'llite', 'llite', 'llite', 'llite', 'llite',
                            'llite', 'llite', 'llite', 'llite', 'llite',
                            'llite', 'llite', 'llite', 'llite', 'llite',
                            'llite', 'llite', 'llite', 'llite', 'llite',
                            'intel_snb','intel_snb', 'intel_snb'],
                      ['CAS_READS', 'CAS_WRITES', 'STALLS',
                       'CLOCKS_UNHALTED_CORE', 'SSE_D_ALL', 'SIMD_D_256',
                       'open','close','mmap','seek','fsync','setattr',
                       'truncate','flock','getattr','statfs','alloc_inode',
                       'setxattr','getxattr',' listxattr',
                       'removexattr', 'inode_permission', 'readdir',
                       'create','lookup',
                       'link','unlink','symlink','mkdir','rmdir','mknod',
                       'rename',
                       'LOAD_OPS_L1_HIT','LOAD_OPS_L2_HIT','LOAD_OPS_LLC_HIT'])
      
      
      
      
      
    except tspl.TSPLException as e:
      continue

    if not tspl_utils.checkjob(ts,3600.,range(1,17)):
      continue

    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    ld=lariat_utils.LariatData(ts.j.id,ts.j.end_time,'lariatData')
    
    read_rate=numpy.zeros_like(tmid)
    write_rate=numpy.zeros_like(tmid)
    stall_rate=numpy.zeros_like(tmid)
    clock_rate=numpy.zeros_like(tmid)
    avx_rate = numpy.zeros_like(tmid)
    sse_rate = numpy.zeros_like(tmid)
    meta_rate = numpy.zeros_like(tmid)
    l1_rate = numpy.zeros_like(tmid)
    l2_rate = numpy.zeros_like(tmid)
    l3_rate = numpy.zeros_like(tmid)

    for k in ts.j.hosts.keys():
      read_rate +=numpy.diff(ts.assemble([0],k,0))/numpy.diff(ts.t)
      write_rate+=numpy.diff(ts.assemble([1],k,0))/numpy.diff(ts.t)
      stall_rate+=numpy.diff(ts.assemble([2],k,0))/numpy.diff(ts.t)
      clock_rate+=numpy.diff(ts.assemble([3],k,0))/numpy.diff(ts.t)
      avx_rate  +=numpy.diff(ts.assemble([5],k,0))/numpy.diff(ts.t)
      sse_rate  +=numpy.diff(ts.assemble([4],k,0))/numpy.diff(ts.t)
      meta_rate +=numpy.diff(ts.assemble(range(5,32),k,0))/numpy.diff(ts.t)
      l1_rate +=numpy.diff(ts.assemble([32],k,0))/numpy.diff(ts.t)
      l2_rate +=numpy.diff(ts.assemble([33],k,0))/numpy.diff(ts.t)
      l3_rate +=numpy.diff(ts.assemble([34],k,0))/numpy.diff(ts.t)
      
    read_rate  /= float(ts.numhosts)
    write_rate /= float(ts.numhosts)
    stall_rate /= float(ts.numhosts)
    clock_rate /= float(ts.numhosts)
    avx_rate   /= float(ts.numhosts)
    sse_rate   /= float(ts.numhosts)
    meta_rate  /= float(ts.numhosts)
    l1_rate  /= float(ts.numhosts)
    l2_rate  /= float(ts.numhosts)
    l3_rate  /= float(ts.numhosts)

    read_frac=read_rate/(read_rate+write_rate+1)
    stall_frac=stall_rate/clock_rate

    title=ts.title
    if ld.exc != 'unknown':
      title += ', E: ' + ld.exc.split('/')[-1]

    fig,ax=plt.subplots(5,1,figsize=(8,8),dpi=80)
    plt.subplots_adjust(hspace=0.35)
    
    plt.suptitle(title)
    ax[0].plot(tmid/3600., read_frac)
    ax[0].set_ylabel('DRAM Read Fraction')
#    ax[0].set_ylim(getlimits(read_frac))
    tspl_utils.adjust_yaxis_range(ax[0],0.1)
    
#    ax[1].plot(tmid/3600., stall_frac)
#    ax[1].set_ylabel('Stall Fraction')
#    tspl_utils.adjust_yaxis_range(ax[1],0.1)

    ax[1].plot(tmid/3600., avx_rate/1e9)
    ax[1].hold=True
    ax[1].plot(tmid/3600., sse_rate/1e9,'r')
    ax[1].set_ylabel('AVX Rate')
    tspl_utils.adjust_yaxis_range(ax[1],0.1)


    ax[2].plot(tmid/3600., clock_rate)
    ax[2].set_ylabel('Observed Clock Rate')
    tspl_utils.adjust_yaxis_range(ax[2],0.1)
    
    ax[3].plot(tmid/3600., meta_rate)
    ax[3].set_ylabel('Meta Data Rate')
    tspl_utils.adjust_yaxis_range(ax[3],0.1)

    ax[4].plot(tmid/3600., l2_rate/(l1_rate+l2_rate+l3_rate))
    ax[4].set_ylabel('Meta Data Rate')
    tspl_utils.adjust_yaxis_range(ax[3],0.1)

    fname='_'.join(['plot',ts.j.id,ts.owner])

    fig.savefig(fname)
    plt.close()

if __name__ == '__main__':
  main()
  
