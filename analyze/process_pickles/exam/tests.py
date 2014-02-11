import os,sys
import abc
import math
import numpy
import operator
import scipy.stats
import multiprocessing

from analyze_conf import lariat_path
from plot import plots
from gen import tspl,tspl_utils,lariat_utils



def unwrap(arg,**kwarg):
  return arg[0].test(*arg[1:],**kwarg)

class Test(object):
  __metaclass__ = abc.ABCMeta

  @abc.abstractproperty
  def k1(self): pass
  @abc.abstractproperty
  def k2(self): pass

  aggregated=True
  ts = None
  ld = None
  plot=False
  def __init__(self,processes=1,aggregated=True,plot=False):
    self.processes=processes
    self.aggregated=aggregated
    self.plot=plot
    manager=multiprocessing.Manager()
    self.results=manager.dict()

 # Build ts object
  def setup(self,jobid,lariat_dict=None,stats=None, 
            ignore_qs=['gpu','gpudev','vis','visdev']):

    try:
      if not self.ts:
        if self.aggregated:
          self.ts=tspl.TSPLSum(jobid,self.k1,self.k2,job_data=stats)
        else:
          self.ts=tspl.TSPLBase(jobid,self.k1,self.k2,job_data=stats)
      if not self.ld:
        if lariat_dict == None:
          self.ld=lariat_utils.LariatData(self.ts.j.id,end_epoch=self.ts.j.end_time,
                                          daysback=3,directory=lariat_path)
        elif lariat_dict == "pass": 
          self.ld=lariat_utils.LariatData(self.ts.j.id)        
        else:
          self.ld=lariat_utils.LariatData(self.ts.j.id,olddata=lariat_dict)
      return
    except tspl.TSPLException as e:
      return
    except EOFError as e:
      print 'End of file found reading: ' + jobid
      return

    if not tspl_utils.checkjob(self.ts,3600,16,ignore_qs): # 1 hour, 16way only
      return
    elif self.ts.numhosts < 2: # At least 2 hosts
      return

  def run(self,filelist,threshold='0.5'):
    if not filelist: return 
    self.thresh=threshold
    pool=multiprocessing.Pool(processes=self.processes) 
    pool.map(unwrap,zip([self]*len(filelist),filelist))

  def comp2thresh(self,jobid,val,func='>'):
    comp = {'>': operator.gt, '>=': operator.ge,
                '<': operator.le, '<=': operator.le,
                '==': operator.eq}

    if comp[func](val, self.thresh):
      self.results[jobid] = True
    else:
      self.results[jobid] = False
    return

  def failed(self):
    results=self.results

    jobs=[]
    for i in results.keys():
      if results[i]:
        jobs.append(i)
    return jobs

  @abc.abstractmethod
  def test(self,jobid):
    """Run the test for a single job"""
    return

class Mem_bw(Test):

  k1=['intel_snb_imc', 'intel_snb_imc']
  k2=['CAS_READS', 'CAS_WRITES']

  def test(self,jobid):
    self.setup(jobid)

    peak = 76.*1.e9
    gdramrate = numpy.zeros(len(self.ts.t)-1)
    for h in self.ts.j.hosts.keys():
      gdramrate += numpy.divide(numpy.diff(64.*self.ts.assemble([0,1],h,0)),
                                numpy.diff(self.ts.t))

    mdr=scipy.stats.tmean(gdramrate)/self.ts.numhosts
    self.comp2thresh(jobid,mdr/peak)

    if self.results[jobid] and self.plot:
      plotter = plots.MasterPlot(self)
      plotter.plot(jobid,threshhold=thresh,prefix='highmembw',
                   header='High Memory Bandwidth',save=True)

      return

class Idle(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','LOAD_L1D_ALL','user'],}

  def test(self,jobid):
    self.setup(jobid)
    mr=[]
    for i in range(len(self.k1)):
      maxrate=numpy.zeros(len(self.ts.t)-1)
      for h in self.ts.j.hosts.keys():
        rate=numpy.divide(numpy.diff(self.ts.data[i][h]),numpy.diff(self.ts.t))
        maxrate=numpy.maximum(rate,maxrate)
      mr.append(maxrate)

    sums=[]
    for i in range(len(self.k1)):
      for h in self.ts.j.hosts.keys():
        rate=numpy.divide(numpy.diff(self.ts.data[i][h]),numpy.diff(self.ts.t))
        sums.append(numpy.sum(numpy.divide(mr[i]-rate,mr[i]))/(len(self.ts.t)-1))

    sums = [0. if math.isnan(x) else x for x in sums]
    val = max(sums)
    self.comp2thresh(jobid,max(sums),'<')

    if self.results[jobid] and self.plot:
      plotter = plots.MasterPlot(self)
      plotter.plot(jobid,prefix='idle_host',header='Idle Host',save=True)

    return

class Imbalance(Test):
  k1=None
  k2=None
  
  def __init__(self,k1,k2,processes=1,aggregated=True,plot=False):
    self.k1=k1
    self.k2=k2
    super(Imbalance,self).__init__(processes=processes,aggregated=aggregated,plot=plot)

  def test(self,jobid):
    self.setup(jobid)
    
    tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
    rng=range(1,len(tmid)) # Throw out first and last
    self.tmid=tmid[rng]         

    maxval=numpy.zeros(len(rng))
    minval=numpy.ones(len(rng))*1e100

    self.rate=[]

    for v in self.ts:
      self.rate.append(numpy.divide(numpy.diff(v)[rng],
                                    numpy.diff(self.ts.t)[rng]))
      maxval=numpy.maximum(maxval,self.rate[-1])
      minval=numpy.minimum(minval,self.rate[-1])

    vals=[]
    mean=[]
    std=[]
    for j in range(len(rng)):
      vals.append([])
      for v in self.rate:
        vals[j].append(v[j])
      mean.append(scipy.stats.tmean(vals[j]))
      std.append(scipy.stats.tstd(vals[j]))

    imbl=maxval-minval

    self.ratio=numpy.divide(std,mean)
    self.ratio2=numpy.divide(imbl,maxval)

    # mean of ratios is the threshold statistic
    self.var=scipy.stats.tmean(self.ratio) 

    self.comp2thresh(jobid,self.var)

    if self.results[jobid] and self.plot:
      plotter = plots.RatioPlot(self)
      plotter.plot(jobid,save=True)
    

class Catastrophe(Test):

  # Hash value must be a list
  k1={'amd64' : ['amd64_sock'],
      'intel_snb': ['intel_snb']}
  k2={'amd64' : ['DRAM'],
      'intel_snb': ['LOAD_L1D_ALL']}

  def compute_fit_params(self,ind):
    fit=[]
    for v in self.ts:
      rate=numpy.divide(numpy.diff(v),numpy.diff(self.ts.t))
      tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
      r1=range(ind)
      r2=[x + ind for x in range(len(rate)-ind)]
      a=numpy.trapz(rate[r1],tmid[r1])/(tmid[ind]-tmid[0])
      b=numpy.trapz(rate[r2],tmid[r2])/(tmid[-1]-tmid[ind])
      fit.append((a,b))      
    return fit   

  def test(self,jobid):
    self.setup(jobid)
    vals=[]

    for i in [x + 2 for x in range(self.ts.size-4)]:
      vals.append(self.compute_fit_params(i))

    vals2=[]
    for v in vals:
      vals2.append([ b/a for (a,b) in v])

    arr=numpy.array(vals2)
    brr=numpy.transpose(arr)

    (m,n)=numpy.shape(brr)

    r=[]
    for i in range(m):
      jnd=numpy.argmin(brr[i,:])
      r.append((jnd,brr[i,jnd]))

    for (ind,ratio) in r:
      self.comp2thresh(jobid,ratio)
      if self.results[jobid]: break

    if self.results[jobid] and self.plot:
      plotter = plots.MasterPlot(self)
      plotter.plot(jobid,prefix='step',header='Step Function Performance',
                   wide=True,save=True)

    return

class FLOPS_test(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL','user'],}

  peak={'amd64' : [2.3e9*16*2, 24e9, 1.],
        'intel_snb' : [ 16*2.7e9*2, 16*2.7e9/2.*64., 1.],}

  def test(self,jobid):
    self.setup(jobid)
    gfloprate = numpy.zeros(len(ts.t)-1)
    gdramrate = numpy.zeros(len(ts.t)-1)
    gcpurate  = numpy.zeros(len(ts.t)-1)
    for h in ts.j.hosts.keys():
      if ts.pmc_type == 'amd64' :
        gfloprate += numpy.divide(numpy.diff(ts.data[0][h][0]),numpy.diff(ts.t))
        gdramrate += numpy.divide(numpy.diff(ts.data[1][h][0]),numpy.diff(ts.t))
        gcpurate  += numpy.divide(numpy.diff(ts.data[2][h][0]),numpy.diff(ts.t))
      elif ts.pmc_type == 'intel_snb':
        gfloprate += numpy.divide(numpy.diff(ts.data[0][h][0]),numpy.diff(ts.t))
        gfloprate += numpy.divide(numpy.diff(ts.data[1][h][0]),numpy.diff(ts.t))
        gdramrate += numpy.divide(numpy.diff(ts.data[2][h][0]),numpy.diff(ts.t))
        gcpurate  += numpy.divide(numpy.diff(ts.data[3][h][0]),numpy.diff(ts.t))
        
    mfr=scipy.stats.tmean(gfloprate)/ts.numhosts
    mdr=scipy.stats.tmean(gdramrate)/ts.numhosts
    mcr=scipy.stats.tmean(gcpurate)/(ts.numhosts*ts.wayness*100.)

    self.comp2thresh(jobid,(mfr/peak[ts.pmc_type][0])/(mdr/peak[ts.pmc_type][1]),'<')

    if self.results[jobid] and self.plot:
      plotter = plots.MasterPlot(self)
      plotter.plot(jobid,save=True,threshold=self.thresh,prefix='lowflops',
                   head='Measured Low Flops',wide=True)

    return

