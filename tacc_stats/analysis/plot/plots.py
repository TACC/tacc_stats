# Plot generation tools for job analysis
from __future__ import print_function
import os
import abc
import numpy,traceback
import multiprocessing

from scipy.stats import scoreatpercentile as score

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_pdf import FigureCanvasPdf

from tacc_stats.cfg import lariat_path
from tacc_stats.analysis.gen import tspl,tspl_utils,lariat_utils,my_utils

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
    print(traceback.format_exc())
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
      print('End of file found reading: ' + jobid)
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

    ax.hold=True

    for k in self.ts.j.hosts.keys():
      v=self.ts.assemble(index,k,0)
      if do_rate:
        val=numpy.divide(numpy.diff(v),numpy.diff(self.ts.t))
      else:
        val=(v[:-1]+v[1:])/(2.0)
      ax.step(self.ts.t/xscale,numpy.append(val,[val[-1]])/yscale,where="post")
    tspl_utils.adjust_yaxis_range(ax,0.1)
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=6))
    self.setlabels(ax,index,xlabel,ylabel,yscale)
    ax.set_xlim([0,self.ts.t[-1]/3600.])
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
    if not self.save:
      self.canvas = FigureCanvasAgg(self.fig)
    else: 
      self.canvas = FigureCanvasPdf(self.fig)
      self.fig.savefig(os.path.join(self.outdir,self.fname))

  @abc.abstractmethod
  def plot(self,jobid,job_data=None):
    """Run the test for a single job"""
    return

