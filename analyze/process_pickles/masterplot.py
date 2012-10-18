#!/usr/bin/env python

import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import math
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('pdf')
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils

# Reduce data from ts object
# add and subtract arrays from data based on sign of index variable in
# accumulator, v
def assemble(data,index,key,jndex):
  v=numpy.zeros_like(data[0][key][jndex])
  for i in index:
    i2=abs(i)
    v+=math.copysign(1,i)*data[i2][key][jndex]
  return v

def setlabels(ax,ts,index,xlabel,ylabel,yscale):
  if xlabel != '':
    ax.set_xlabel(xlabel)
  if ylabel != '':
    ax.set_ylabel(ylabel)
  else:
    ax.set_ylabel('Total ' + ts.label(ts.k1[index[0]],
                                      ts.k2[index[0]],yscale) + '/s' )

# Consolidate several near identical plots to a function
# Plots lines for each host
def plot_lines(ax, ts, index, xscale=1.0, yscale=1.0, xlabel='', ylabel=''):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  ax.hold=True
  for k in ts.j.hosts.keys():
    v=assemble(ts.data,index,k,0)
    rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
    ax.plot(tmid/xscale,rate/yscale)
  tspl_utils.adjust_yaxis_range(ax,0.1)
  ax.yaxis.set_major_locator( matplotlib.ticker.MaxNLocator(nbins=6))
  setlabels(ax,ts,index,xlabel,ylabel,yscale)

# Plots "time histograms" for every host
# This code is likely inefficient
def plot_thist(ax, ts, index, xscale=1.0, yscale=1.0, xlabel='', ylabel=''):
  d=[]
  for k in ts.j.hosts.keys():
    v=assemble(ts.data,index,k,0)
    d.append(numpy.divide(numpy.diff(v),numpy.diff(ts.t)))
  a=numpy.array(d)

  h=[]
  mn=numpy.min(a)
  mn=min(0.,mn)
  mx=numpy.max(a)
  n=float(len(ts.j.hosts.keys()))
  for i in range(len(ts.t)-1):
    hist=numpy.histogram(a[:,i],30,(mn,mx))
    h.append(hist[0])

  h2=numpy.transpose(numpy.array(h))

  ax.pcolor(ts.t/xscale,hist[1]/yscale,h2,
            edgecolors='none',rasterized=True,cmap='spectral')

  setlabels(ax,ts,index,xlabel,ylabel,yscale)

  ax.yaxis.set_major_locator( matplotlib.ticker.MaxNLocator(nbins=4))


def master_plot(file,do_hist,threshold=False,output_dir='.'):
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

  if do_hist:
    plot=plot_thist
  else:
    plot=plot_lines
  
  # Plot SSE FLOPS
  plot(ax[0],ts,[0],3600.)
    
  # Plot DCSF rate
  plot(ax[1],ts,[1],3600.,1e9)

  #Plot DRAM rate
  plot(ax[2],ts,[2],3600.,1e9)
  
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  # Plot lnet sum rate
  plot(ax[3],ts,[3,4],3600.,1024.**2,ylabel='Total lnet MB/s')

  # Plot remaining IB sum rate
  plot(ax[4],ts,[5,6,-3,-4],3600.,1024.**2,ylabel='Total (ib_sw-lnet) MB/s') 

  #Plot CPU user time
  plot(ax[5],ts,[7],3600.,ts.wayness*100.,
       xlabel='Time (hr)',
       ylabel='Total cpu user\nfraction')
  
  print ts.j.id + ': '

  title=ts.title
  if threshold:
    title+=', V: %(v)-8.3f' % {'v': threshold}

  plt.suptitle(title)
  plt.subplots_adjust(hspace=0.35)

  fname='_'.join(['graph',ts.j.id,ts.j.acct['owner'],'master'])
  if do_hist:
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
    master_plot(file,n.hist)


if __name__ == '__main__':
  main()
  
