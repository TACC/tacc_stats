#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('pdf')
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils

def master_plot(file,threshold=False,output_dir='.'):
  k1=['amd64_core','amd64_core','amd64_sock','lnet','lnet','ib_sw','ib_sw',
      'cpu']
  k2=['SSE_FLOPS','DCSF','DRAM','rx_bytes','tx_bytes','rx_bytes','tx_bytes',
      'user']

  try:
    print file
    ts=tspl.TSPLSum(file,k1,k2)
  except tspl.TSPLException as e:
    return

  if not tspl_utils.checkjob(ts,3600,16):
    return
  elif ts.numhosts < 2:
    print ts.j.id + ': 1 host'
    return

  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  

  fig,ax=plt.subplots(6,1,figsize=(8,12),dpi=80)
  
  # Plot flop rate
  ax[0].hold=True 
  for k in ts.j.hosts.keys():
    h=ts.j.hosts[k]
    rate=numpy.divide(numpy.diff(ts.data[0][k][0]),numpy.diff(ts.t))
    ax[0].plot(tmid/3600,rate)
  ax[0].set_ylabel('Total ' + ts.label(k1[1],k2[0]) +  '/s')

  # Plot DCSF rate
  ax[1].hold=True
  for k in ts.j.hosts.keys():
    h=ts.j.hosts[k]
    rate=numpy.divide(numpy.diff(ts.data[1][k][0])/1e9,numpy.diff(ts.t))
    ax[1].plot(tmid/3600,rate)
  ax[1].set_ylabel('Total ' + ts.label(k1[1],k2[1],1e9) + '/s')

  #Plot DRAM rate
  ax[2].hold=True
  for k in ts.j.hosts.keys():
    h=ts.j.hosts[k]
    rate=numpy.divide(numpy.diff(ts.data[2][k][0])/1e9,numpy.diff(ts.t))
    ax[2].plot(tmid/3600,rate)
  ax[2].set_ylabel('Total ' + ts.label(k1[2],k2[2],1e9) +  '/s')

  # Plot lnet sum rate
  ax[3].hold=True
  for k in ts.j.hosts.keys():
    h=ts.j.hosts[k]
    rate=numpy.divide(numpy.diff(ts.data[3][k][0]+ts.data[4][k][0]),
                      numpy.diff(ts.t))
    ax[3].plot(tmid/3600,rate/(1024.*1024.))
  ax[3].set_ylabel('Total lnet MB/s')

  # Plot remaining IB sum rate
  ax[4].hold=True
  for k in ts.j.hosts.keys():
    h=ts.j.hosts[k]
    v=ts.data[5][k][0]+ts.data[6][k][0]-(ts.data[3][k][0]+ts.data[4][k][0])
    rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
    ax[4].plot(tmid/3600,rate/(1024*1024.))
  ax[4].set_ylabel('Total (ib_sw-lnet) MB/s')

  #Plot CPU user time
  ax[5].hold=True
  for k in ts.j.hosts.keys():
    h=ts.j.hosts[k]
    rate=numpy.divide(numpy.diff(ts.data[7][k][0]/100/ts.wayness),
                      numpy.diff(ts.t))
    ax[5].plot(tmid/3600,rate)
  ax[5].set_ylabel('Total user cpu\nfraction/s')
  ax[5].set_xlabel('Time (hr)')
  
  print ts.j.id + ': '

  title=ts.title
  if threshold:
    title+=', V: %(v)-8.3f' % {'v': threshold}

  plt.suptitle(title)
  plt.subplots_adjust(hspace=0.35)
  for a in ax:
    tspl_utils.adjust_yaxis_range(a,0.1)

  fname='_'.join(['graph',ts.j.id,ts.j.acct['owner'],'master'])
  fig.savefig(output_dir+'/'+fname)
  plt.close()


def main():

  parser = argparse.ArgumentParser(description='Plot important stats for jobs')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)
  for file in filelist:
    master_plot(file)


if __name__ == '__main__':
  main()
  
