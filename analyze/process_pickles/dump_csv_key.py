#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl

def main():

  parser = argparse.ArgumentParser(description='Dump CSV for a key pair for some jobs')
  parser.add_argument('key1', help='First key', nargs='?',
                      default='amd64_core')
  parser.add_argument('key2', help='Second key', nargs='?',
                      default='SSE_FLOPS')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args(sys.argv[1:])

  filelist=tspl.getfilelist(n.filearg)

  print  sys.argv[3]
  
  for file in filelist:
    try:
      ts=tspl.TSPickleLoader(file,[n.key1],[n.key2])
    except Exception as inst:
      print type(inst)     # the exception instance
      print inst           # __str__ allows args to printed directly
      continue

    if not tspl.checkjob(ts,3600,16):
      continue
    elif ts.numhosts < 2:
      print ts.j.id + ': 1 host'
      continue

    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    rate={}
    for k in ts.j.hosts.keys():
      rate[k]=numpy.divide(numpy.diff(ts.data[0][k]),numpy.diff(ts.t))
      for i in range(len(tmid)):
        print ','.join([ts.j.id,k,str(tmid[i]),str(rate[k][i])])
     

if __name__ == '__main__':
  main()
  
