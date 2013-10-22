#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils

def main():

  parser = argparse.ArgumentParser(description='Dump CSV for a key pair for some jobs')
  parser.add_argument('-k1', help='Set first key',
                      nargs='+', type=str, default=['amd64_sock'])
  parser.add_argument('-k2', help='Set second key',
                      nargs='+', type=str, default=['DRAM'])
  parser.add_argument('-f', help='File, directory, or quoted'
                      ' glob pattern', nargs=1, type=str, default=['jobs'])
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.f[0])

  for file in filelist:
    try:
      ts=tspl.TSPLSum(file,n.k1,n.k2)
    except tspl.TSPLException as e:
      continue

    if not tspl_utils.checkjob(ts,0,16):
      continue
    elif ts.numhosts < 2:
      print ts.j.id + ': 1 host'
      continue

    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    for k in ts.j.hosts.keys():
      rates=[numpy.divide(numpy.diff(ts.data[x][k][0]),numpy.diff(ts.t))
             for x in range(len(ts.data))]
      for i in range(len(tmid)):
        v=[rates[x][i] for x in range(len(ts.data))]
        print ','.join([ts.j.id,k,str(tmid[i])]+[str(x) for x in v])
     

if __name__ == '__main__':
  main()
  
