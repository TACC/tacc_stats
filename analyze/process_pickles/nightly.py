#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import numpy
import scipy, scipy.stats
import argparse
import re
import tspl, tspl_utils, imbalance, masterplot

def main():
  parser=argparse.ArgumentParser(description='Deal with a directory of pickle'
                                 ' files nightly')
  parser.add_argument('threshold', help='Treshold ratio for std dev:mean',
                      nargs='?', default=0.25)
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  ratios={}
  imbalance.compute_imbalance(ratios,filelist,['amd64_core'],['SSE_FLOPS'],
                              float(n.threshold),False,False)

  badfiles=[]
  th=[]
  for i in ratios.keys():
    v=ratios[i][0]
    if v > float(n.threshold):
      for f in filelist:
        if re.search(i,f):
          badfiles.append(f)
          th.append(v)

  masterplot.master_plot(badfiles,th)
  
if __name__ == "__main__":
  main()
