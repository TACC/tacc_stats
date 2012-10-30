#!/usr/bin/env python
import sys
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
  masterplot.master_plot(file,'lines',thresh,out_dir,'lowflops',
                         header='Measured Low Flops')
  masterplot.master_plot(file,'percentile',thresh,out_dir,'lowflops',
                         header='Measured Low Flops')

def do_floppy(file,thresh,floppy):
  floppy[file]=is_unfloppy(file,thresh)

def is_unfloppy(file,thresh):
  k1=['amd64_core','amd64_sock','cpu']
  k2=['SSE_FLOPS', 'DRAM',      'user']
  peak=[ 2.3e9*16*2, 24e9, 1.]
  
  try:
    ts=tspl.TSPLSum(file,k1,k2)
  except tspl.TSPLException as e:
    return

  if not tspl_utils.checkjob(ts,3600,[x+1 for x in range(16)]): # 1 hour
    return
  elif ts.numhosts < 2: # At least 2 hosts
    print ts.j.id + ': 1 host'
    return

  gfloprate = numpy.zeros(len(ts.t)-1)
  gdramrate = numpy.zeros(len(ts.t)-1)
  gcpurate  = numpy.zeros(len(ts.t)-1)
  for h in ts.j.hosts.keys():
    gfloprate += numpy.divide(numpy.diff(ts.data[0][h][0]),numpy.diff(ts.t))
    gdramrate += numpy.divide(numpy.diff(ts.data[1][h][0]),numpy.diff(ts.t))
    gcpurate  += numpy.divide(numpy.diff(ts.data[2][h][0]),numpy.diff(ts.t))

    mfr=scipy.stats.tmean(gfloprate)/ts.numhosts
    mdr=scipy.stats.tmean(gdramrate)/ts.numhosts
    mcr=scipy.stats.tmean(gcpurate)/(ts.numhosts*ts.wayness*100.)

  #print [ts.j.id,mfr/peak[0],mdr/peak[1],mcr/peak[2]]

  if ( (mcr/peak[2] > 0.5 ) and
       (mfr/peak[0])/(mdr/peak[1]) < thresh ):
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

  pool.map(partial_floppy,filelist)

  badjobs=[]
  for i in floppy.keys():
    if floppy[i]:
      badjobs.append(i)
  
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
  
