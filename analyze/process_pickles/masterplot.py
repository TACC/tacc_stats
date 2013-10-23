#!/usr/bin/env python
import analyze_conf,sys
import datetime, glob, job_stats, os, subprocess, time
import math
import matplotlib
# Set the matplotlib output mode from config if it exists
if not 'matplotlib.pyplot' in sys.modules:
  try:
    matplotlib.use(analyze_conf.matplotlib_output_mode)
  except NameError:
    matplotlib.use('pdf')
    
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import multiprocessing, functools
import tspl, tspl_utils, lariat_utils, my_utils

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
def plot_lines(ax, ts, index, xscale=1.0, yscale=1.0, xlabel='', ylabel='',
               do_rate=True):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  ax.hold=True
  for k in ts.j.hosts.keys():
    v=ts.assemble(index,k,0)
    if do_rate:
      rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
      ax.plot(tmid/xscale,rate/yscale)
    else:
      val=(v[:-1]+v[1:])/2.0
      ax.plot(tmid/xscale,val/yscale)
  tspl_utils.adjust_yaxis_range(ax,0.1)
  ax.yaxis.set_major_locator(  matplotlib.ticker.MaxNLocator(nbins=6))
  setlabels(ax,ts,index,xlabel,ylabel,yscale)

# Plots "time histograms" for every host
# This code is likely inefficient
def plot_thist(ax, ts, index, xscale=1.0, yscale=1.0, xlabel='', ylabel='',
               do_rate=False):
  d=[]
  for k in ts.j.hosts.keys():
    v=ts.assemble(index,k,0)
    if do_rate:
      d.append(numpy.divide(numpy.diff(v),numpy.diff(ts.t)))
    else:
      d.append((v[:-1]+v[1:])/2.0)
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
  ax.autoscale(tight=True)

def plot_mmm(ax, ts, index, xscale=1.0, yscale=1.0, xlabel='', ylabel='',
             do_rate=False):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  d=[]
  for k in ts.j.hosts.keys():
    v=ts.assemble(index,k,0)
    if do_rate:
      d.append(numpy.divide(numpy.diff(v),numpy.diff(ts.t)))
    else:
      d.append((v[:-1]+v[1:])/2.0)
    
  a=numpy.array(d)

  mn=[]
  p25=[]
  p50=[]
  p75=[]
  mx=[]
  for i in range(len(ts.t)-1):
    mn.append(min(a[:,i]))
    p25.append(scipy.stats.scoreatpercentile(a[:,i],25))
    p50.append(scipy.stats.scoreatpercentile(a[:,i],50))
    p75.append(scipy.stats.scoreatpercentile(a[:,i],75))
    mx.append(max(a[:,i]))

  mn=numpy.array(mn)
  p25=numpy.array(p25)
  p50=numpy.array(p50)
  p75=numpy.array(p75)
  mx=numpy.array(mx)

  ax.hold=True
  ax.plot(tmid/xscale,mn/yscale,'--')
  ax.plot(tmid/xscale,p25/yscale)
  ax.plot(tmid/xscale,p50/yscale)
  ax.plot(tmid/xscale,p75/yscale)
  ax.plot(tmid/xscale,mx/yscale,'--')

  setlabels(ax,ts,index,xlabel,ylabel,yscale)
  ax.yaxis.set_major_locator( matplotlib.ticker.MaxNLocator(nbins=4))
  tspl_utils.adjust_yaxis_range(ax,0.1)

def master_plot(file,mode='lines',threshold=False,
                output_dir='.',prefix='graph',mintime=3600,wayness=16,
                header='Master'):
  k1={'amd64' :
      ['amd64_core','amd64_core','amd64_sock','lnet','lnet',
       'ib_sw','ib_sw','cpu'],
      'intel' : ['intel_pmc3', 'intel_pmc3', 'intel_pmc3', 
                 'lnet', 'lnet', 'ib_sw','ib_sw','cpu'],
      'intel_snb' : ['intel_snb_imc', 'intel_snb_imc', 'intel_snb', 
                     'lnet', 'lnet', 'ib_sw','ib_sw','cpu',
                     'intel_snb', 'intel_snb', 'mem', 'mem'],
      }
  
  k2={'amd64':
      ['SSE_FLOPS','DCSF','DRAM','rx_bytes','tx_bytes',
       'rx_bytes','tx_bytes','user'],
      'intel' : ['PMC3', 'PMC2', 'FIXED_CTR0',
                 'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes','user'],
      'intel_snb' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes','user',
                     'SSE_D_ALL', 'SIMD_D_256', 'MemUsed', 'AnonPages'],
      }

  try:
    print file
    ts=tspl.TSPLSum(file,k1,k2)
  except tspl.TSPLException as e:
    return 

  ignore_qs=['gpu','gpudev','vis','visdev']
  if not tspl_utils.checkjob(ts,mintime,wayness,ignore_qs):
    return

  fig,ax=plt.subplots(6,1,figsize=(8,12),dpi=80)
  ax=my_utils.flatten(ax)

  if mode == 'hist':
    plot=plot_thist
  elif mode == 'percentile':
    plot=plot_mmm
  else:
    plot=plot_lines

  if ts.pmc_type == 'intel_snb' :
    # Plot key 1
    plot(ax[0],ts,[8,9],3600.,1e9,
         ylabel='Total AVX +\nSSE Ginst/s')
    
    # Plot key 2
    plot(ax[1],ts,[0,1],3600.,1.0/64.0*1024.*1024.*1024.,
         ylabel='Total Mem BW GB/s')

    #Plot key 3
    #plot(ax[2],ts,[2],3600.,1.0/64.0*1e9, ylabel='L1 BW GB/s')
    plot(ax[2],ts,[10,-11],3600.,1024.0*1024.0*1024.0, ylabel='Memory Usage GB',
         do_rate=False)
  else: #Fix this to support the old amd plots
    print ts.pmc_type + ' not supported'
    return 
  
  # Plot lnet sum rate
  plot(ax[3],ts,[3,4],3600.,1024.**2,ylabel='Total lnet MB/s')

  # Plot remaining IB sum rate
  plot(ax[4],ts,[5,6,-3,-4],3600.,1024.**2,ylabel='Total (ib_sw-lnet) MB/s') 

  #Plot CPU user time
  plot(ax[5],ts,[7],3600.,ts.wayness*100.,
       xlabel='Time (hr)',
       ylabel='Total cpu user\nfraction')
  
  print ts.j.id + ': '
  print 'cc'
  title=header+'\n'+ts.title
  if threshold:
    title+=', V: %(v)-6.1f' % {'v': threshold}
  ld=lariat_utils.LariatData(ts.j.id,ts.j.end_time,analyze_conf.lariat_path)
  title += '\n' + ld.title()
  print 'dd'
  
  plt.suptitle(title)
  plt.subplots_adjust(hspace=0.35)

  fname='_'.join([prefix,ts.j.id,ts.owner,'master'])
  if mode == 'hist':
    fname+='_hist'
  elif mode == 'percentile':
    fname+='_perc'
    
  fig.savefig(output_dir+'/'+fname)
  plt.close()

  return fig

def mp_wrapper(file,mode='lines',threshold=False,
                output_dir='.',prefix='graph',mintime=3600,wayness=16,
                header='Master',figs=[]):
  master_plot(file,mode,threshold,output_dir,prefix,mintime,wayness,header)

def main():

  parser = argparse.ArgumentParser(description='Plot important stats for jobs')
  parser.add_argument('-m', help='Plot mode: lines, hist, percentile',
                      nargs=1, type=str, default=['lines'],
                      metavar='mode')
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-s', help='Set minimum time in seconds',
                      nargs=1, type=int, default=[3600])
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)
  procs  = min(len(filelist),n.p[0])

  if procs < 1:
    print 'Must have at least one file'
    exit(1)
    
  pool = multiprocessing.Pool(processes=procs)

  partial_master=functools.partial(mp_wrapper,mode=n.m[0],
                                   threshold=False,
                                   output_dir=n.o[0],
                                   prefix='graph',
                                   mintime=n.s[0],
                                   wayness=[x+1 for x in range(16)])
  
  pool.map(partial_master,filelist)
  
  pool.close()
  pool.join()

if __name__ == '__main__':
  main()
  
