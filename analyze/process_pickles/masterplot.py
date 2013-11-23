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
import cPickle as pickle

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
                header='Master',lariat_dict=None,wide=False,job_stats=None):
  k1={'amd64' :
      ['amd64_core','amd64_core','amd64_sock','lnet','lnet',
       'ib_sw','ib_sw','cpu'],
      'intel' : ['intel_pmc3', 'intel_pmc3', 'intel_pmc3', 
                 'lnet', 'lnet', 'ib_ext','ib_ext','cpu','mem','mem'],
      'intel_snb' : ['intel_snb_imc', 'intel_snb_imc', 'intel_snb', 
                     'lnet', 'lnet', 'ib_sw','ib_sw','cpu',
                     'intel_snb', 'intel_snb', 'mem', 'mem'],
      }
  
  k2={'amd64':
      ['SSE_FLOPS','DCSF','DRAM','rx_bytes','tx_bytes',
       'rx_bytes','tx_bytes','user'],
      'intel' : ['MEM_LOAD_RETIRED_L1D_HIT', 'FP_COMP_OPS_EXE_X87', 
                 'INSTRUCTIONS_RETIRED', 'rx_bytes','tx_bytes', 
                 'port_recv_data','port_xmit_data','user', 'MemUsed', 'AnonPages'],
      'intel_snb' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes','user',
                     'SSE_D_ALL', 'SIMD_D_256', 'MemUsed', 'AnonPages'],
      }

  try:
    print file
    ts=tspl.TSPLSum(file,k1,k2,job_stats)
  except tspl.TSPLException as e:
    return 
  
  ignore_qs=[]#'gpu','gpudev','vis','visdev']
  if not tspl_utils.checkjob(ts,mintime,wayness,ignore_qs):
    return

  if lariat_dict == None:
    ld=lariat_utils.LariatData(ts.j.id,end_epoch=ts.j.end_time,daysback=3,directory=analyze_conf.lariat_path)
  elif lariat_dict == "pass": ld = lariat_utils.LariatData(ts.j.id)
  else:
    ld=lariat_utils.LariatData(ts.j.id,olddata=lariat_dict)

    

  wayness=ts.wayness
  if ld.wayness != -1 and ld.wayness < ts.wayness:
    wayness=ld.wayness

  if wide:
    fig,ax=plt.subplots(6,2,figsize=(15.5,12),dpi=110)

    # Make 2-d array into 1-d, and reorder so that the left side is blank
    ax=my_utils.flatten(ax)
    ax_even=ax[0:12:2]
    ax_odd =ax[1:12:2]
    ax=ax_odd + ax_even
    
    for a in ax_even:
      a.axis('off')
  else:
    fig,ax=plt.subplots(6,1,figsize=(8,12),dpi=110)

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
  elif ts.pmc_type == 'intel':
    plot(ax[0],ts,[1],3600.,1e9,ylabel='FP Ginst/s')
    plot(ax[2],ts,[8,-9],3600.,1024.0*1024.0*1024.0, ylabel='Memory Usage GB',do_rate=False)
  else: 
    #Fix this to support the old amd plots
    print ts.pmc_type + ' not supported'
    return 

  # Plot lnet sum rate
  plot(ax[3],ts,[3,4],3600.,1024.**2,ylabel='Total lnet MB/s')

  # Plot remaining IB sum rate
  if ts.pmc_type == 'intel_snb' :
    plot(ax[4],ts,[5,6,-3,-4],3600.,1024.**2,ylabel='Total (ib_sw-lnet) MB/s') 
  elif ts.pmc_type == 'intel' :
    plot(ax[4],ts,[5,6,-3,-4],3600.,1024.**2,ylabel='Total (ib_ext-lnet) MB/s') 

  #Plot CPU user time
  plot(ax[5],ts,[7],3600.,wayness*100.,
       xlabel='Time (hr)',
       ylabel='Total cpu user\nfraction')
  
  print ts.j.id + ': '
  
  plt.subplots_adjust(hspace=0.35)
  if wide:
    left_text=header+'\n'+my_utils.summary_text(ld,ts)
    text_len=len(left_text.split('\n'))
    fontsize=ax[0].yaxis.label.get_size()
    linespacing=1.2
    fontrate=float(fontsize*linespacing)/72./15.5
    yloc=.8-fontrate*(text_len-1) # this doesn't quite work. fontrate is too
                                  # small by a small amount
    plt.figtext(.05,yloc,left_text,linespacing=linespacing)
    fname='_'.join([prefix,ts.j.id,ts.owner,'wide_master'])
  elif header != None:
    title=header+'\n'+ts.title
    if threshold:
      title+=', V: %(v)-6.1f' % {'v': threshold}
    title += '\n' + ld.title()
    plt.suptitle(title)
    fname='_'.join([prefix,ts.j.id,ts.owner,'master'])
  else:
    fname='_'.join([prefix,ts.j.id,ts.owner,'master'])

  if mode == 'hist':
    fname+='_hist'
  elif mode == 'percentile':
    fname+='_perc'
    

  plt.close()

  return fig, fname

def mp_wrapper(file,mode='lines',threshold=False,
                output_dir='.',prefix='graph',mintime=3600,wayness=16,
                header='Master',figs=[],lariat_dict=None, wide=False):
  ret = master_plot(file,mode,threshold,output_dir,prefix,
                    mintime,wayness,header,lariat_dict,wide)
  if ret != None:
    fig, fname = ret
    fig.savefig(output_dir+'/'+fname)

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
  parser.add_argument('-w', help='Set wide plot format', action='store_true')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)
  procs  = min(len(filelist),n.p[0])

  job=pickle.load(open(filelist[0]))
  jid=job.id
  epoch=job.end_time

  ld=lariat_utils.LariatData(jid,end_epoch=epoch,daysback=3,directory=analyze_conf.lariat_path)
  
  if procs < 1:
    print 'Must have at least one file'
    exit(1)
    
  pool = multiprocessing.Pool(processes=procs)

  partial_master=functools.partial(mp_wrapper,mode=n.m[0],
                                   threshold=False,
                                   output_dir=n.o[0],
                                   prefix='graph',
                                   mintime=n.s[0],
                                   wayness=[x+1 for x in range(16)],
                                   lariat_dict=ld.ld,
                                   wide=n.w)
  
  pool.map(partial_master,filelist)
  
  pool.close()
  pool.join()

if __name__ == '__main__':
  main()
  
