## @package plot
#
# Plot generation tools for job analysis

import os
import abc
import math
import numpy
import multiprocessing
import matplotlib
from scipy.stats import scoreatpercentile as score
matplotlib.use('pdf')
import matplotlib.pyplot as plt
import job_stats
from analysis_conf import lariat_path,matplotlib_output_mode
from analysis.gen import tspl,tspl_utils,lariat_utils,my_utils

## Multiprocessing Unwrapper
#
# Multiprocessor module cannot work with class objects.
# This unwrapper accepts a Plot class and extracts the
# class method plot.
def unwrap(arg):
  kwarg = arg[2]
  return arg[0].plot(arg[1],**kwarg)

## Plot Class
#
# This is an abstract base class for plotting.
class Plot(object):
  __metaclass__ = abc.ABCMeta
  fig=None
  ## Stat data object
  ts=None
  ## Lariat data object
  ld=None
  ## Aggregate cores in nodes flag
  aggregate=True

  ## Default constructor
  def __init__(self,processes=1,**kwarg):
    self.processes=processes

  ## Plot the list of files using multiprocessing
  def run(self,filelist,**kwargs):
    if not filelist: return 
    pool=multiprocessing.Pool(processes=self.processes) 
    pool.map(unwrap,zip([self]*len(filelist),filelist,[kwargs]*len(filelist)))
    pool.close()
    pool.join()

  ## Set the x and y axis labels for a plot
  def setlabels(self,ax,index,xlabel,ylabel,yscale):
    if xlabel != '':
      ax.set_xlabel(xlabel)
    if ylabel != '':
      ax.set_ylabel(ylabel)
    else:
      ax.set_ylabel('Total '+self.ts.label(self.ts.k1[index[0]],
                                      self.ts.k2[index[0]],yscale)+'/s' )
  def setup(self,jobid,k1,k2,job_data=None):
    if self.aggregate:
      self.ts=tspl.TSPLSum(jobid,self.k1,self.k2,job_data=job_data)
    else:
      self.ts=tspl.TSPLBase(jobid,self.k1,self.k2,job_data=job_data)
      if self.ld != 'pass':
        self.ld.set_job(self.ts.j.id,
                        end_epoch=self.ts.j.end_time,
                        directory=lariat_path,daysback=3)

  # Plots lines for each host
  def plot_lines(self,ax,index,xscale=1.0,yscale=1.0,xlabel='',ylabel='',
                 do_rate=True):

    tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
    ax.hold=True
    for k in self.ts.j.hosts.keys():

      v=self.ts.assemble(index,k,0)
      if do_rate:
        rate=numpy.divide(numpy.diff(v),numpy.diff(self.ts.t))
        ax.plot(tmid/xscale,rate/yscale)
      else:
        val=(v[:-1]+v[1:])/2.0
        ax.plot(tmid/xscale,val/yscale)
    tspl_utils.adjust_yaxis_range(ax,0.1)
    ax.yaxis.set_major_locator(  matplotlib.ticker.MaxNLocator(nbins=6))
    self.setlabels(ax,index,xlabel,ylabel,yscale)

  # Plots "time histograms" for every host
  # This code is likely inefficient
  def plot_thist(self,ax,index,xscale=1.0,yscale=1.0,xlabel='',ylabel='',
                 do_rate=False):
    d=[]
    for k in self.ts.j.hosts.keys():
      v=self.ts.assemble(index,k,0)
      if do_rate:
        d.append(numpy.divide(numpy.diff(v),numpy.diff(self.ts.t)))
      else:
        d.append((v[:-1]+v[1:])/2.0)
    a=numpy.array(d)

    h=[]
    mn=numpy.min(a)
    mn=min(0.,mn)
    mx=numpy.max(a)
    n=float(len(self.ts.j.hosts.keys()))
    for i in range(len(self.ts.t)-1):
      hist=numpy.histogram(a[:,i],30,(mn,mx))
      h.append(hist[0])

    h2=numpy.transpose(numpy.array(h))

    ax.pcolor(self.ts.t/xscale,hist[1]/yscale,h2,
              edgecolors='none',rasterized=True,cmap='spectral')
    self.setlabels(ax,self.ts,index,xlabel,ylabel,yscale)
    ax.autoscale(tight=True)

  def plot_mmm(self,ax,index,xscale=1.0,yscale=1.0,xlabel='',ylabel='',
               do_rate=False):

    tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
    d=[]
    for k in self.ts.j.hosts.keys():
      v=self.ts.assemble(index,k,0)
      if do_rate:
        d.append(numpy.divide(numpy.diff(v),numpy.diff(self.ts.t)))
      else:
        d.append((v[:-1]+v[1:])/2.0)

    a=numpy.array(d)

    mn=[]
    p25=[]
    p50=[]
    p75=[]
    mx=[]
    for i in range(len(self.ts.t)-1):
      mn.append(min(a[:,i]))
      p25.append(score(a[:,i],25))
      p50.append(score(a[:,i],50))
      p75.append(score(a[:,i],75))
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

    self.setlabels(ax,index,xlabel,ylabel,yscale)
    ax.yaxis.set_major_locator( matplotlib.ticker.MaxNLocator(nbins=4))
    tspl_utils.adjust_yaxis_range(ax,0.1)

  @abc.abstractmethod
  def plot(self,jobid):
    """Run the test for a single job"""
    return


class MasterPlot(Plot):
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

  fname='master'

  def plot(self,jobid,mode='lines',
           threshold=False,ld=None,
           prefix='graph',mintime=3600,
           wayness=16,save=False,outdir='.',
           header='Master',wide=False,job_data=None):

    self.ld=ld
    self.setup(jobid,self.k1,self.k2,job_data=job_data)

    wayness=self.ts.wayness
    if ld != 'pass':
      if self.ld.wayness != -1 and self.ld.wayness < self.ts.wayness:
        wayness=self.ld.wayness
      
    if wide:
      self.fig,ax=plt.subplots(6,2,figsize=(15.5,12),dpi=110)

      # Make 2-d array into 1-d, and reorder so that the left side is blank
      ax=my_utils.flatten(ax)
      ax_even=ax[0:12:2]
      ax_odd =ax[1:12:2]
      ax=ax_odd + ax_even

      for a in ax_even:
        a.axis('off')
    else:
      self.fig,ax=plt.subplots(6,1,figsize=(8,12),dpi=110)

    if mode == 'hist':
      plot=self.plot_thist
    elif mode == 'percentile':
      plot=self.plot_mmm
    else:
      plot=self.plot_lines

    k1_tmp=self.k1[self.ts.pmc_type]
    k2_tmp=self.k2[self.ts.pmc_type]


    if self.ts.pmc_type == 'intel_snb' :
      # Plot key 1
      idx0=k2_tmp.index('SSE_D_ALL')
      idx1=k2_tmp.index('SIMD_D_256')
      plot(ax[0],[idx0,idx1],3600.,1e9,
           ylabel='Total AVX +\nSSE Ginst/s')

      # Plot key 2
      idx0=k2_tmp.index('CAS_READS')
      idx1=k2_tmp.index('CAS_WRITES')
      plot(ax[1], [idx0,idx1], 3600., 1.0/64.0*1024.*1024.*1024., ylabel='Total Mem BW GB/s')
    elif self.ts.pmc_type == 'intel':
      idx0=k2_tmp.index('FP_COMP_OPS_EXE_X87')
      plot(ax[0], [idx0], 3600., 1e9, ylabel='FP Ginst/s')
    else: 
      #Fix this to support the old amd plots
      print self.ts.pmc_type + ' not supported'
      return 

    #Plot key 3
    idx0=k2_tmp.index('MemUsed')
    idx1=k2_tmp.index('AnonPages')
    plot(ax[2], [idx0,-idx1], 3600.,2.**30.0, ylabel='Memory Usage GB',do_rate=False)

    # Plot lnet sum rate
    idx0=k1_tmp.index('lnet')
    idx1=idx0 + k1_tmp[idx0+1:].index('lnet') + 1

    plot(ax[3], [idx0,idx1], 3600., 1024.**2, ylabel='Total lnet MB/s')

    # Plot remaining IB sum rate
    if self.ts.pmc_type == 'intel_snb' :
      idx2=k1_tmp.index('ib_sw')
      idx3=idx2 + k1_tmp[idx2+1:].index('ib_sw') + 1
    if self.ts.pmc_type == 'intel':
      idx2=k1_tmp.index('ib_ext')
      idx3=idx2 + k1_tmp[idx2+1:].index('ib_ext') + 1

    plot(ax[4],[idx2,idx3,-idx0,-idx1],3600.,2.**20,
         ylabel='Total (ib-lnet) MB/s') 

    #Plot CPU user time
    idx0=k2_tmp.index('user')
    plot(ax[5],[idx0],3600.,wayness*100.,
         xlabel='Time (hr)',
         ylabel='Total cpu user\nfraction')

    plt.subplots_adjust(hspace=0.35)
    if wide:
      left_text=header+'\n'+my_utils.summary_text(self.ld,self.ts)
      text_len=len(left_text.split('\n'))
      fontsize=ax[0].yaxis.label.get_size()
      linespacing=1.2
      fontrate=float(fontsize*linespacing)/72./15.5
      yloc=.8-fontrate*(text_len-1) # this doesn't quite work. fontrate is too
                                    # small by a small amount
      plt.figtext(.05,yloc,left_text,linespacing=linespacing)
      self.fname='_'.join([prefix,self.ts.j.id,self.ts.owner,'wide_master'])
    elif header != None:
      title=header+'\n'+self.ts.title
      if threshold:
        title+=', V: %(v)-6.1f' % {'v': threshold}
      title += '\n' + self.ld.title()
      plt.suptitle(title)
      self.fname='_'.join([prefix,self.ts.j.id,self.ts.owner,'master'])
    else:
      self.fname='_'.join([prefix,self.ts.j.id,self.ts.owner,'master'])

    if mode == 'hist':
      self.fname+='_hist'
    elif mode == 'percentile':
      self.fname+='_perc'

    plt.close()
    if save:
      self.fig.savefig(os.path.join(outdir,self.fname))
    return self.fig
class MemUsage(Plot):
  k1=['mem','mem']
  k2=['MemUsed','AnonPages']
  
  def plot(self,jobid,save=False,outdir='.'):

    if ts==None or ld==None:
      data=self.setup(jobid,self.k1,self.k2)
      self.ts=data.ts
      self.ld=data.ld
    else:
      self.ts=ts
      self.ld=ld

    fig,ax=plt.subplots(1,1,figsize=(8,8),dpi=80)

    for k in self.ts.j.hosts.keys():
      m=self.ts.data[0][k][0]-self.ts.data[1][k][0]
      m-=self.ts.data[0][k][0][0]
      ax.plot(self.ts.t/3600.,m)

    ax.set_ylabel('MemUsed - AnonPages ' +
                  self.ts.j.get_schema(self.ts.k1[0])[self.ts.k2[0]].unit)
    ax.set_xlabel('Time (hr)')
    plt.suptitle(self.ts.title)

    if save:
      fname='graph_'+self.ts.j.id+'_'+self.ts.k1[0]+'_'+self.ts.k2[0]
      fig.savefig(fname)
    plt.close()

class RatioPlot(Plot):

  def __init__(self,imbalance,processes=1):
    self.imbalance=imbalance
    super(RatioPlot,self).__init__(processes=processes)

  def plot(self,jobid,save=False,outdir='.'):
    if not self.imbalance: 
      print "Generate ratio data using Imbalance test first for job",jobid
      return

    imb = self.imbalance
  
    # Compute y-axis min and max, expand the limits by 10%
    ymin=min(numpy.minimum(imb.ratio,imb.ratio2))
    ymax=max(numpy.maximum(imb.ratio,imb.ratio2))
    ymin,ymax=tspl_utils.expand_range(ymin,ymax,0.1)

    fig,ax=plt.subplots(2,1,figsize=(8,8),dpi=80)

    ax[0].plot(imb.tmid/3600,imb.ratio)
    ax[0].hold=True
    ax[0].plot(imb.tmid/3600,imb.ratio2)
    ax[0].legend(('Std Dev','Max Diff'), loc=4)
    ax[1].hold=True

    ymin1=0. # This is wrong in general, but we don't want the min to be > 0.
    ymax1=0.

    for v in imb.rate:
      ymin1=min(ymin1,min(v))
      ymax1=max(ymax1,max(v))
      ax[1].plot(imb.tmid/3600,v)

    ymin1,ymax1=tspl_utils.expand_range(ymin1,ymax1,0.1)
    
    title=imb.ts.title
    if imb.ld.exc != 'unknown':
      title += ', E: ' + imb.ld.exc.split('/')[-1]
    title += ', V: %(V)-8.3g' % {'V' : imb.var}
    plt.suptitle(title)
    ax[0].set_xlabel('Time (hr)')
    ax[0].set_ylabel('Imbalance Ratios')
    ax[1].set_xlabel('Time (hr)')
    ax[1].set_ylabel('Total ' + imb.ts.label(imb.ts.k1[0],imb.ts.k2[0]) 
                     + '/s')
    ax[0].set_ylim(bottom=ymin,top=ymax)
    ax[1].set_ylim(bottom=ymin1,top=ymax1)

    if imb.aggregate: full=''
    else: full='_full'

    imb.fname='_'.join(['graph',imb.ts.j.id,imb.ts.owner,
                    imb.ts.k1[0],imb.ts.k2[0],'imb'+full])

    plt.close()
    if save:
      fig.savefig(os.path.join(outdir,imb.fname))

class MetaDataRate(Plot):
  k1=['llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', ]
  k2=['open','close','mmap','fsync','setattr',
      'truncate','flock','getattr','statfs','alloc_inode',
      'setxattr',' listxattr',
      'removexattr', 'readdir',
      'create','lookup','link','unlink','symlink','mkdir',
      'rmdir','mknod','rename',]

  def __init__(self,mdrate,processes=1):
    self.mdrate=mdrate
    super(MetaDataRate,self).__init__(processes=processes)

  def plot(self,jobid,save=False,outdir='.'):
    if not self.mdrate: 
      print "Generate MetaDataRate test data first for job",jobid
      return

    mdrate = self.mdrate
    ld = mdrate.ld
    ts = mdrate.ts

    title=ts.title
    if ld.exc != 'unknown':
      title += ', E: ' + ld.exc.split('/')[-1]

    fig,ax=plt.subplots(1,1,figsize=(10,8),dpi=80)
    plt.subplots_adjust(hspace=0.35)
    plt.suptitle(title)

    markers = ('o','x','+','^','s','8','p',
                 'h','*','D','<','>','v','d','.')

    colors  = ('b','g','r','c','m','k','y')

    cnt=0
    for v in ts.data:
      for host in v:
        for vals in v[host]:
          rate=numpy.diff(vals)/numpy.diff(ts.t)
          c=colors[cnt % len(colors)]
          m=markers[cnt % len(markers)]

          ax.plot(tmid/3600., rate, marker=m,
                  markeredgecolor=c, linestyle='-', color=c,
                  markerfacecolor='None', label=k2[cnt])
          ax.hold=True
      cnt=cnt+1

    ax.set_ylabel('Meta Data Rate (op/s)')
    tspl_utils.adjust_yaxis_range(ax,0.1)

    handles,labels=ax.get_legend_handles_labels()
    new_handles={}
    for h,l in zip(handles,labels):
      new_handles[l]=h

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])
    ax.legend(new_handles.values(),new_handles.keys(),prop={'size':8},
              bbox_to_anchor=(1.05,1), borderaxespad=0., loc=2)

    fname='_'.join(['metadata',ts.j.id,ts.owner])
    if self.save: fig.savefig(fname)

    plt.close()


class HeatMap(Plot):

  def __init__(self,k1,k2):
    self.aggregate = False
    self.k1 = k1
    self.k2 = k2

  def plot(self,jobid,save=False,outdir='.',ld=None,job_data=None):
    self.ld=ld
    self.setup(jobid,self.k1,self.k2,job_data=job_data)
    ts=self.ts

    cpi = numpy.array([])
    hosts = []
    for v in ts.data[0]:
        hosts.append(v)
        ncores = len(ts.data[0][v])
        for k in range(ncores):
            i = numpy.array(ts.data[0][v][k],dtype=numpy.float)
            c = numpy.array(ts.data[1][v][k],dtype=numpy.float)
            ratio = numpy.divide(numpy.diff(i),numpy.diff(c))
            if not cpi.size: cpi = numpy.array([ratio])
            else: cpi = numpy.vstack((cpi,ratio))
    cpi_min, cpi_max = cpi.min(), cpi.max()

    self.fig,ax=plt.subplots(1,1,figsize=(8,12),dpi=110)

    ycore = numpy.arange(cpi.shape[0]+1)
    time = ts.t/3600.

    yhost=numpy.arange(len(hosts)+1)*ncores + ncores

    fontsize = 10

    if len(yhost) > 80:
        fontsize /= 0.5*numpy.log(len(yhost))

    plt.yticks(yhost - ncores/2.,hosts,size=fontsize)
    plt.pcolormesh(time, ycore, cpi, vmin=cpi_min, vmax=cpi_max)
    plt.axis([time.min(),time.max(),ycore.min(),ycore.max()])

    plt.title('Instructions Retired per Core Clock Cycle')
    plt.colorbar()

    ax.set_xlabel('Time (hrs)')

    plt.close()

    return self.fig
