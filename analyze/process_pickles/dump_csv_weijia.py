#!/usr/bin/env python

import sys
import analyze_conf
import datetime, glob, job_stats, os, subprocess, time
import numpy
import scipy, scipy.stats
import argparse
import multiprocessing
import tspl, tspl_utils, lariat_utils

def do_compute(file):
  try:
    ts=tspl.TSPLSum(file,['intel_snb_imc', 'intel_snb_imc',
                          'intel_snb', 'intel_snb', 'intel_snb',
                          'intel_snb', 'intel_snb'],
                    ['CAS_READS', 'CAS_WRITES',
                     'LOAD_L1D_ALL', 'SIMD_D_256', 'SSE_D_ALL',
                     'STALLS', 'CLOCKS_UNHALTED_CORE'])

  except tspl.TSPLException as e:
    return

  if not tspl_utils.checkjob(ts,0,16):
    return
  elif ts.numhosts < 2:
    print ts.j.id + ': 1 host'
    return

  ignore_qs=['gpu','gpudev','vis','visdev']
  if not tspl_utils.checkjob(ts,3600.,range(1,33),ignore_qs):
    return
  
  ld=lariat_utils.LariatData(ts.j.id,ts.j.end_time,
                             '/scratch/projects/lariatData')
  if ld.exc == 'unknown':
    return
  
  tmid=(ts.t[:-1]+ts.t[1:])/2.0

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

  read_rate  /= ts.numhosts
  write_rate /= ts.numhosts
  l1_rate    /= ts.numhosts
  avx_rate   /= ts.numhosts
  sse_rate   /= ts.numhosts
  stall_rate /= ts.numhosts
  clock_rate /= ts.numhosts
    

  data_ratio  = (read_rate+write_rate)/l1_rate
  flops       = avx_rate+sse_rate
  flops_ratio = (flops-numpy.min(flops))/(numpy.max(flops)-numpy.min(flops))
  stall_ratio = stall_rate/clock_rate

  mean_data_ratio  = numpy.mean(data_ratio)
  mean_stall_ratio = numpy.mean(stall_ratio)
  mean_flops       = numpy.mean(flops)


  ename=ld.exc.split('/')[-1]
  ename=ld.comp_name(ename,ld.equiv_patterns)
  mean_mem_rate=numpy.mean(read_rate + write_rate)
  if mean_mem_rate > 2e9: # Put a print in here and investigate bad jobs
    return

  return ','.join([ts.j.id,ts.owner,ename,
                   str(mean_mem_rate),str(mean_stall_ratio),
                   str(mean_data_ratio),str(mean_flops)])



def main():

  parser = argparse.ArgumentParser(description='Dump CSV keys for Weijia.')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')

  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)
  pool   = multiprocessing.Pool(processes=n.p[0])

  if len(filelist) !=0:
    res=pool.map(do_compute,filelist)
    pool.close()
    pool.join()

  with open('dump.csv','w') as file:
    file.write('# Job Id, Username, Executable, Mean DRAM BW, ' +
               'Mean Stall Fraction, Mean DRAM/L1, Mean Flops\n')
  
    for line in res:
      if line:
        file.write(line+'\n')


if __name__ == '__main__':
  main()
  
