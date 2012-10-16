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


# Consolidate several near identical plots to a function
# Plots lines for each host
def plot_lines(ax, ts, index, xscale=1.0, yscale=1.0, xlabel='', ylabel=''):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  ax.hold=True
  for k in ts.j.hosts.keys():
    rate=numpy.divide(numpy.diff(ts.data[index][k][0]),numpy.diff(ts.t))
    ax.plot(tmid/xscale,rate/yscale)
  if xlabel != '':
    ax.set_xlabel(xlabel)
  if ylabel != '':
    ax.set_ylabel(ylabel)
  else:
    ax.set_ylabel('Total ' + ts.label(ts.k1[index],ts.k2[index],yscale) + '/s' )
  tspl_utils.adjust_yaxis_range(ax,0.1)

# Plots "time histograms" for every host
# This code is likely inefficient
def plot_thist(ax, ts, index, xscale=1.0, yscale=1.0, xlabel='', ylabel=''):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  d=[]
  for k in ts.j.hosts.keys():
    d.append(numpy.divide(numpy.diff(ts.data[index][k][0]),numpy.diff(ts.t)))
  a=numpy.array(d)

  h=[]
  mn=numpy.min(a)
  mx=numpy.max(a)
  n=float(len(ts.j.hosts.keys()))
  for i in range(len(tmid)):
    hist=numpy.histogram(a[:,i],n,(mn,mx))
    h.append(hist[0])

  h2=numpy.transpose(numpy.array(h))

  ax.pcolor(tmid/xscale,hist[1],h2,edgecolors='none')

  if xlabel != '':
    ax.set_xlabel(xlabel)
  if ylabel != '':
    ax.set_ylabel(ylabel)
  else:
    ax.set_ylabel('Total ' + ts.label(ts.k1[index],ts.k2[index],yscale) + '/s' )


def master_plot(file,n,threshold=False,output_dir='.'):
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

  fig,ax=plt.subplots(6,1,figsize=(8,12),dpi=80)
  
  # Plot SSE FLOPS
  if n.hist:
    plot_thist(ax[0],ts,0,3600.)
  else:
    plot_lines(ax[0],ts,0,3600.)
    
  # Plot DCSF rate
  if n.hist:
    plot_thist(ax[1],ts,1,3600.,1e9)
  else:
    plot_lines(ax[1],ts,1,3600.,1e9)

  #Plot DRAM rate
  if n.hist:
    plot_thist(ax[2],ts,2,3600.,1e9)
  else:
    plot_lines(ax[2],ts,2,3600.,1e9)
  
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
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
  plot_lines(ax[5],ts,7,3600.,ts.wayness*100.,
             xlabel='Time (hr)',
             ylabel='Total cpu user\nfraction')
  
  print ts.j.id + ': '

  title=ts.title
  if threshold:
    title+=', V: %(v)-8.3f' % {'v': threshold}

  plt.suptitle(title)
  plt.subplots_adjust(hspace=0.35)

  fname='_'.join(['graph',ts.j.id,ts.j.acct['owner'],'master'])
  if n.hist:
    fname+='_hist'
  fig.savefig(output_dir+'/'+fname)
  plt.close()


def main():

  parser = argparse.ArgumentParser(description='Plot important stats for jobs')
  parser.add_argument('--hist',help='Plot Time Histograms', action='store_true')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)
  for file in filelist:
    master_plot(file,n)


if __name__ == '__main__':
  main()
  
