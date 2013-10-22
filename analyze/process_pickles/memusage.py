#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import cPickle as pickle
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
import scipy
import argparse
import tspl, tspl_utils

def main():
  
  parser = argparse.ArgumentParser(description='Plot MemUsed-AnonPages for jobs')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()
  filelist=tspl_utils.getfilelist(n.filearg)

  for file in filelist:
    try:
      ts=tspl.TSPLSum(file,['mem','mem'],['MemUsed','AnonPages'])
    except tspl.TSPLException as e:
      continue

    if not tspl_utils.checkjob(ts,3600,16):
      continue
    else:
      print ts.j.id
      
    fig=plt.figure()
    ax=fig.gca()
    ax.hold=True
    for k in ts.j.hosts.keys():
      m=ts.data[0][k][0]-ts.data[1][k][0]
      m-=ts.data[0][k][0][0]
      ax.plot(ts.t/3600.,m)

    ax.set_ylabel('MemUsed - AnonPages ' +
                  ts.j.get_schema(ts.k1[0])[ts.k2[0]].unit)
    ax.set_xlabel('Time (hr)')
    plt.suptitle(ts.title)

    fname='graph_'+ts.j.id+'_'+ts.k1[0]+'_'+ts.k2[0]+'.png'
    fig.savefig(fname)
    plt.close()

if __name__ == "__main__":
  main()
  

  
