## @package plot
#
# Plot generation tools for job analysis
import os
import abc
import math
import numpy,traceback
import multiprocessing
import matplotlib
matplotlib.use('Agg')
from scipy.stats import scoreatpercentile as score
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from sys_conf import lariat_path
from ..gen import tspl,tspl_utils,lariat_utils,my_utils

## Multiprocessing Unwrapper
#
# Multiprocessor module cannot work with class objects.
# This unwrapper accepts a Plot class and extracts the
# class method plot.
def unwrap(arg):
  try:
    kwarg = arg[2]
    return arg[0].plot(arg[1],**kwarg)
  except:
    traceback.format_exc()
## Plot Class
#
# This is an abstract base class for plotting.
class Plot(object):
  __metaclass__ = abc.ABCMeta

  fig = Figure()

  ts=None

  ## Default constructor
  def __init__(self,processes=1,**kwargs):
    self.processes=processes
    self.mode=kwargs.get('mode','lines')
    self.threshold=kwargs.get('threshold',None)
    self.outdir=kwargs.get('outdir','.')
    self.prefix=kwargs.get('prefix','')
    self.header=kwargs.get('header',None)
    self.wide=kwargs.get('wide',False)
    self.save=kwargs.get('save',False)
    self.lariat_data=kwargs.get('lariat_data',
                                lariat_utils.LariatData(directory=lariat_path,
                                                        daysback=2))
    self.aggregate=kwargs.get('aggregate',True)

  def setup(self,jobid,job_data=None):
    try:
      if self.aggregate:
        self.ts=tspl.TSPLSum(jobid,self.k1,self.k2,job_data=job_data)
      else:
        self.ts=tspl.TSPLBase(jobid,self.k1,self.k2,job_data=job_data)
    except tspl.TSPLException as e:
      return False
    except EOFError as e:
      print 'End of file found reading: ' + jobid
      return False

    if self.lariat_data != 'pass':
      self.lariat_data.set_job(self.ts)

    return True

  ## Plot the list of files using multiprocessing
  def run(self,filelist,**kwargs):
    if not filelist: return 

    # Cache the Lariat Data Dict
    self.setup(filelist[0])
    self.setup(filelist[-1])

    pool=multiprocessing.Pool(processes=self.processes) 
    pool.map(unwrap,zip([self]*len(filelist),filelist,[kwargs]*len(filelist)))

  ## Set the x and y axis labels for a plot
  def setlabels(self,ax,index,xlabel,ylabel,yscale):
    if xlabel != '':
      ax.set_xlabel(xlabel)
    if ylabel != '':
      ax.set_ylabel(ylabel)
    else:
      ax.set_ylabel('Total '+self.ts.label(self.ts.k1[index[0]],
                                      self.ts.k2[index[0]],yscale)+'/s' )
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
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=6))
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

  def output(self,file_suffix):    
    if self.wide:
      if self.lariat_data != 'pass':
        left_text=self.header+'\n'+my_utils.summary_text(self.lariat_data,self.ts)
      else: left_text=self.header + '\n' + self.ts.title
      text_len=len(left_text.split('\n'))
      fontsize=self.ax.yaxis.label.get_size()
      linespacing=1.2
      fontrate=float(fontsize*linespacing)/72./15.5
      yloc=.8-fontrate*(text_len-1) # this doesn't quite work. fontrate is too
                                    # small by a small amount
      self.fig.text(.05,yloc,left_text,linespacing=linespacing)
      self.fname='_'.join([self.prefix,self.ts.j.id,self.ts.owner,'wide_'+file_suffix])
    elif self.header != None:
      title=self.header+'\n'+self.ts.title
      if self.threshold:
        title+=', V: %(v)-6.1f' % {'v': self.threshold}
      if self.lariat_data != 'pass': title += '\n' + self.lariat_data.title()
      self.fig.suptitle(title)
      self.fname='_'.join([self.prefix,self.ts.j.id,self.ts.owner,file_suffix])
    else:
      self.fname='_'.join([self.prefix,self.ts.j.id,self.ts.owner,file_suffix])

    if self.mode == 'hist':
      self.fname+='_hist'
    elif self.mode == 'percentile':
      self.fname+='_perc'
    self.canvas = FigureCanvas(self.fig)
    if self.save: 
      self.fig.savefig(os.path.join(self.outdir,self.fname))

  @abc.abstractmethod
  def plot(self,jobid,job_data=None):
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

  def plot(self,jobid,job_data=None):
    if not self.setup(jobid,job_data=job_data): return
    
    wayness=self.ts.wayness
    if self.lariat_data != 'pass':
      if self.lariat_data.wayness != -1 and self.lariat_data.wayness < self.ts.wayness:
        wayness=self.lariat_data.wayness
    
    if self.wide:
      self.fig = Figure(figsize=(15.5,12),dpi=110)
      self.ax=self.fig.add_subplot(6,2,2)
      cols = 2
      shift = 2
    else:
      self.fig = Figure(figsize=(8,12),dpi=110)
      self.ax=self.fig.add_subplot(6,1,1)
      cols = 1
      shift = 1
    if self.mode == 'hist':
      plot=self.plot_thist
    elif self.mode == 'percentile':
      plot=self.plot_mmm
    else:
      plot=self.plot_lines

    k1_tmp=self.k1[self.ts.pmc_type]
    k2_tmp=self.k2[self.ts.pmc_type]

    if self.ts.pmc_type == 'intel_snb' :
      # Plot key 1
      idx0=k2_tmp.index('SSE_D_ALL')
      idx1=k2_tmp.index('SIMD_D_256')
      plot(self.fig.add_subplot(6,cols,1*shift),[idx0,idx1],3600.,1e9,
           ylabel='Total AVX +\nSSE Ginst/s')

      # Plot key 2
      idx0=k2_tmp.index('CAS_READS')
      idx1=k2_tmp.index('CAS_WRITES')
      plot(self.fig.add_subplot(6,cols,2*shift), [idx0,idx1], 3600., 1.0/64.0*1024.*1024.*1024., ylabel='Total Mem BW GB/s')
    elif self.ts.pmc_type == 'intel':
      idx0=k2_tmp.index('FP_COMP_OPS_EXE_X87')
      plot(self.fig.add_subplot(6,cols,2*shift), [idx0], 3600., 1e9, ylabel='FP Ginst/s')
    else: 
      #Fix this to support the old amd plots
      print self.ts.pmc_type + ' not supported'
      return 

    #Plot key 3
    idx0=k2_tmp.index('MemUsed')
    idx1=k2_tmp.index('AnonPages')
    plot(self.fig.add_subplot(6,cols,3*shift), [idx0,-idx1], 3600.,2.**30.0, ylabel='Memory Usage GB',do_rate=False)

    # Plot lnet sum rate
    idx0=k1_tmp.index('lnet')
    idx1=idx0 + k1_tmp[idx0+1:].index('lnet') + 1

    plot(self.fig.add_subplot(6,cols,4*shift), [idx0,idx1], 3600., 1024.**2, ylabel='Total lnet MB/s')

    # Plot remaining IB sum rate
    if self.ts.pmc_type == 'intel_snb' :
      idx2=k1_tmp.index('ib_sw')
      idx3=idx2 + k1_tmp[idx2+1:].index('ib_sw') + 1
    if self.ts.pmc_type == 'intel':
      idx2=k1_tmp.index('ib_ext')
      idx3=idx2 + k1_tmp[idx2+1:].index('ib_ext') + 1

    plot(self.fig.add_subplot(6,cols,5*shift),[idx2,idx3,-idx0,-idx1],3600.,2.**20,
         ylabel='Total (ib-lnet) MB/s') 

    #Plot CPU user time
    idx0=k2_tmp.index('user')
    plot(self.fig.add_subplot(6,cols,6*shift),[idx0],3600.,wayness*100.,
         xlabel='Time (hr)',
         ylabel='Total cpu user\nfraction')

    self.fig.subplots_adjust(hspace=0.35)
    self.output('master')

class MemUsage(Plot):
  k1=['mem','mem']
  k2=['MemUsed','AnonPages']
  
  def plot(self,jobid,job_data=None):

    self.setup(jobid,job_data=job_data)
    self.fig=Figure(figsize=(8,8),dpi=80)
    self.ax=self.fig.add_subplot(1,1,1)
    self.ax = [self.ax]

    for k in self.ts.j.hosts.keys():
      m=self.ts.data[0][k][0]-self.ts.data[1][k][0]
      m-=self.ts.data[0][k][0][0]
      self.ax[0].plot(self.ts.t/3600.,m)

    self.ax[0].set_ylabel('MemUsed - AnonPages ' +
                  self.ts.j.get_schema(self.ts.k1[0])[self.ts.k2[0]].unit)
    self.ax[0].set_xlabel('Time (hr)')

    self.output('memusage')

class RatioPlot(Plot):

  def __init__(self,imbalance,processes=1):
    self.imbalance=imbalance
    super(RatioPlot,self).__init__(processes=processes)

  def plot(self,jobid,job_data=None):
    if not self.imbalance: 
      print "Generate ratio data using Imbalance test first for job",jobid
      return

    imb = self.imbalance
  
    # Compute y-axis min and max, expand the limits by 10%
    ymin=min(numpy.minimum(imb.ratio,imb.ratio2))
    ymax=max(numpy.maximum(imb.ratio,imb.ratio2))
    ymin,ymax=tspl_utils.expand_range(ymin,ymax,0.1)

    self.ax=self.fig.subplots(2,1,figsize=(8,8),dpi=80)

    self.ax[0].plot(imb.tmid/3600,imb.ratio)
    self.ax[0].hold=True
    self.ax[0].plot(imb.tmid/3600,imb.ratio2)
    self.ax[0].legend(('Std Dev','Max Diff'), loc=4)
    self.ax[1].hold=True

    ymin1=0. # This is wrong in general, but we don't want the min to be > 0.
    ymax1=0.

    for v in imb.rate:
      ymin1=min(ymin1,min(v))
      ymax1=max(ymax1,max(v))
      self.ax[1].plot(imb.tmid/3600,v)

    ymin1,ymax1=tspl_utils.expand_range(ymin1,ymax1,0.1)
    
    title=imb.ts.title
    if imb.lariat_data.exc != 'unknown':
      title += ', E: ' + imb.lariat_data.exc.split('/')[-1]
    title += ', V: %(V)-8.3g' % {'V' : imb.var}
    self.fig.suptitle(title)
    ax[0].set_xlabel('Time (hr)')
    ax[0].set_ylabel('Imbalance Ratios')
    ax[1].set_xlabel('Time (hr)')
    ax[1].set_ylabel('Total ' + imb.ts.label(imb.ts.k1[0],imb.ts.k2[0]) 
                     + '/s')
    ax[0].set_ylim(bottom=ymin,top=ymax)
    ax[1].set_ylim(bottom=ymin1,top=ymax1)

    if imb.aggregate: full=''
    else: full='_full'

    self.output('ratio_'+full)

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

  def plot(self,jobid,job_data=None):
    self.setup(jobid,job_data=job_data)

    ts = self.ts
    self.fig = Figure(figsize=(10,8),dpi=80)
    self.ax=self.fig.add_subplot(1,1,1)
    self.ax=[self.ax]
    self.fig.subplots_adjust(hspace=0.35)

    markers = ('o','x','+','^','s','8','p',
                 'h','*','D','<','>','v','d','.')

    colors  = ('b','g','r','c','m','k','y')
    tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
    cnt=0
    for v in ts.data:
      for host in v:
        for vals in v[host]:
          rate=numpy.diff(vals)/numpy.diff(ts.t)
          c=colors[cnt % len(colors)]
          m=markers[cnt % len(markers)]

          self.ax[0].plot(tmid/3600., rate, marker=m,
                  markeredgecolor=c, linestyle='-', color=c,
                  markerfacecolor='None', label=self.k2[cnt])
          self.ax[0].hold=True
      cnt=cnt+1

    self.ax[0].set_ylabel('Meta Data Rate (op/s)')
    tspl_utils.adjust_yaxis_range(self.ax[0],0.1)

    handles,labels=self.ax[0].get_legend_handles_labels()
    new_handles={}
    for h,l in zip(handles,labels):
      new_handles[l]=h

    box = self.ax[0].get_position()
    self.ax[0].set_position([box.x0, box.y0, box.width * 0.9, box.height])
    self.ax[0].legend(new_handles.values(),new_handles.keys(),prop={'size':8},
                      bbox_to_anchor=(1.05,1), borderaxespad=0., loc=2)

    self.output('metadata')

class HeatMap(Plot):

  def __init__(self,k1=['intel_snb','intel_snb'],
               k2=['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
               processes=1,aggregate=False,**kwargs):
    #self.aggregate = False
    self.k1 = k1
    self.k2 = k2
    super(HeatMap,self).__init__(processes=processes,aggregate=aggregate,**kwargs)

  def plot(self,jobid,job_data=None):
    self.setup(jobid,job_data=job_data)
    ts=self.ts

    hosts = []
    for v in ts.data[0]:
        hosts.append(v)
        ncores = len(ts.data[0][v])
        for k in range(ncores):
          num = numpy.array(numpy.diff(ts.data[0][v][k]),dtype=numpy.float64)
          den = numpy.array(numpy.diff(ts.data[1][v][k]),dtype=numpy.float64)
          ratio = numpy.divide(num,den)
          ratio = numpy.nan_to_num(ratio)
          try: cpi = numpy.vstack((cpi,ratio))
          except: cpi = numpy.array([ratio]) 

    cpi_min, cpi_max = cpi.min(), cpi.max()

    mean_cpi = numpy.mean(cpi)
    var_cpi  = numpy.var(cpi)
    self.fig = Figure(figsize=(8,12),dpi=110)
    self.ax=self.fig.add_subplot(1,1,1)

    ycore = numpy.arange(cpi.shape[0]+1)
    time = ts.t/3600.
    yhost=numpy.arange(len(hosts)+1)*ncores + ncores

    fontsize = 10

    if len(yhost) > 80:
        fontsize /= 0.5*numpy.log(len(yhost))
    self.ax.set_ylim(bottom=ycore.min(),top=ycore.max())
    self.ax.set_yticks(yhost[0:-1]-ncores/2.)
    self.ax.set_yticklabels(hosts)#,va='center')
    self.ax.set_xlim(left=time.min(),right=time.max())

    pcm = self.ax.pcolormesh(time, ycore, cpi)
    numpy.set_printoptions(precision=4)
    try: self.ax.set_title(self.k2[ts.pmc_type][0] +'/'+self.k2[ts.pmc_type][1] + '\n'+ r'$\bar{Mean}=$'+'{0:.2f}'.format(mean_cpi)+' '+r'$Var=$' +  '{0:.2f}'.format(var_cpi))
    except: self.ax.set_title(self.k2[0] +'/'+self.k2[1] + '\n'+ r'$\bar{Mean}$='+'{0:.2f}'.format(mean_cpi)+' '+r'$Var=$' +  '{0:.2f}'.format(var_cpi))
    self.fig.colorbar(pcm)
    self.ax.set_xlabel('Time (hrs)')
    self.output('heatmap')

class DevPlot(Plot):

  def __init__(self,k1,k2,processes=1,**kwargs):
    self.k1 = k1
    self.k2 = k2
    super(DevPlot,self).__init__(processes=processes,**kwargs)

  def plot(self,jobid,job_data=None):
    self.setup(jobid,job_data=job_data)
    cpu_name = self.ts.pmc_type
    type_name=self.k1[cpu_name][0]
    events = self.k2[cpu_name]

    ts=self.ts

    n_events = len(events)
    self.fig = Figure(figsize=(8,n_events*2),dpi=80)

    do_rate = True
    scale = 1.0
    if type_name == 'mem': 
      do_rate = False
      scale=2.0**10
    if type_name == 'cpu':
      scale=ts.wayness*100.0

    for i in range(n_events):
      self.ax = self.fig.add_subplot(n_events,1,i+1)
      self.plot_lines(self.ax, [i], 3600., yscale=scale, do_rate = do_rate)
      self.ax.set_ylabel(events[i],size='small')
    self.ax.set_xlabel("Time (hr)")
    self.fig.subplots_adjust(hspace=0.0)
    self.fig.tight_layout()

    self.output('devices')
"""
class HistPlot(Plot):

  def __init__(self,k1,k2,processes=1,**kwargs):
    self.k1 = k1
    self.k2 = k2
    super(HistPlot,self).__init__(processes=processes,**kwargs)

  def plot(self,jobid,job_data=None):
    self.setup(jobid,job_data=job_data)


    ts=self.ts
"""
