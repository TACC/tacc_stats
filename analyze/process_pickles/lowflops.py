#!/usr/bin/env python
import analyze_conf
import sys
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

  masterplot.mp_wrapper(file,'lines',thresh,out_dir,'lowflops',
                         header='Measured Low Flops', wide=True)
  masterplot.mp_wrapper(file,'percentile',thresh,out_dir,'lowflops',
                         header='Measured Low Flops (Percentile)', wide=True)

def do_floppy(file,thresh,floppy):
  floppy[file]=is_unfloppy(file,thresh)

def is_unfloppy(file,thresh):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL','user'],}

  peak={'amd64' : [2.3e9*16*2, 24e9, 1.],
        'intel_snb' : [ 16*2.7e9*2, 16*2.7e9/2.*64., 1.],}
  
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

  gfloprate = numpy.zeros(len(ts.t)-1)
  gdramrate = numpy.zeros(len(ts.t)-1)
  gcpurate  = numpy.zeros(len(ts.t)-1)
  for h in ts.j.hosts.keys():
    if ts.pmc_type == 'amd64' :
      gfloprate += numpy.divide(numpy.diff(ts.data[0][h][0]),numpy.diff(ts.t))
      gdramrate += numpy.divide(numpy.diff(ts.data[1][h][0]),numpy.diff(ts.t))
      gcpurate  += numpy.divide(numpy.diff(ts.data[2][h][0]),numpy.diff(ts.t))
    elif ts.pmc_type == 'intel_snb':
      gfloprate += numpy.divide(numpy.diff(ts.data[0][h][0]),numpy.diff(ts.t))
      gfloprate += numpy.divide(numpy.diff(ts.data[1][h][0]),numpy.diff(ts.t))
      gdramrate += numpy.divide(numpy.diff(ts.data[2][h][0]),numpy.diff(ts.t))
      gcpurate  += numpy.divide(numpy.diff(ts.data[3][h][0]),numpy.diff(ts.t))
      

  mfr=scipy.stats.tmean(gfloprate)/ts.numhosts
  mdr=scipy.stats.tmean(gdramrate)/ts.numhosts
  mcr=scipy.stats.tmean(gcpurate)/(ts.numhosts*ts.wayness*100.)

  print mfr/peak[ts.pmc_type][0], (mdr/peak[ts.pmc_type][1])

  # [ts.j.id,mfr/peak[0],mdr/peak[1],mcr/peak[2]
  #print 'mcr',mcr/peak[ts.pmc_type][2], (mfr/peak[ts.pmc_type][0])/(mdr/peak[ts.pmc_type][1])
  if ( (mcr/peak[ts.pmc_type][2] > 0.5 ) and
       (mfr/peak[ts.pmc_type][0])/(mdr/peak[ts.pmc_type][1]) < thresh ):
    return True
  else:
    return False

def main():
  parser = argparse.ArgumentParser(description='Find jobs with low flops but'
                                   'reasonable levels of other activity.')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-t', metavar='threshold',
                      help='Treshold flopiness',
                      nargs=1, type=float, default=[0.001])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()
  
  filelist=tspl_utils.getfilelist(n.filearg)

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  floppy = m.dict()
  thresh = n.t[0]
  outdir = n.o[0]
  
  partial_floppy=functools.partial(do_floppy,thresh=thresh,floppy=floppy)

  if len(filelist) != 0:
    pool.map(partial_floppy,filelist)
    pool.close()
    pool.join()

  badjobs=[]
  for i in floppy.keys():
    if floppy[i]:
      badjobs.append(i)
  

  pool   = multiprocessing.Pool(processes=n.p[0])
  if len(badjobs) != 0:
    pool.map(do_mp,zip(badjobs,
                       [thresh for x in range(len(badjobs))],
                       [outdir for x in range(len(badjobs))])) 
    pool.close()
    pool.join()


  print '----------- Low Flops -----------'
  for i in badjobs:
    print i.split('/')[-1]
  
if __name__ == '__main__':
  main()
  
