#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import cPickle as pickle
import matplotlib.pyplot as plt
import numpy
import scipy
import argparse
import tspl

def main():
  
  parser = argparse.ArgumentParser(description='Plot MemUsed-AnonPages for jobs')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()
  filelist=tspl.getfilelist(n.filearg)

  for file in filelist:
    try:
      ts=tspl.TSPickleLoader(file,['mem','mem'],['MemUsed','AnonPages'])
    except Exception as inst:
      print type(inst)     # the exception instance
      print inst           # __str__ allows args to printed directly
      continue

    if not tspl.checkjob(ts,3600,16):
      continue
    else:
      print ts.j.id
      
    fig=plt.figure()
    ax=fig.gca()
    ax.hold=True
    for k in ts.j.hosts.keys():
      m=ts.data[0][k]-ts.data[1][k]
      m-=ts.data[0][k][0]
      ax.plot(ts.t,m)

    ax.set_title(ts.title)

    fname='graph_'+ts.j.id+'_'+ts.k1[0]+'_'+ts.k2[0]+'.png'
    fig.savefig(fname)
    plt.close()

if __name__ == "__main__":
  main()
  

  
