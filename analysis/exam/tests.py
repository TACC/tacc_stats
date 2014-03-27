import os,sys
import abc
import math
import numpy
import operator
from scipy.stats import tmean,tstd
import multiprocessing
from pickler import job_stats, batch_acct
sys.modules['job_stats'] = job_stats
sys.modules['batch_acct'] = batch_acct
from sys_conf import lariat_path
from ..gen import lariat_utils,tspl,tspl_utils

def unwrap(arg,**kwarg):
  try:
    return arg[0].test(*arg[1:],**kwarg)
  except: pass

class Test(object):
  __metaclass__ = abc.ABCMeta

  @abc.abstractproperty
  def k1(self): pass
  @abc.abstractproperty
  def k2(self): pass

  ts = None

  def __init__(self,processes=1,**kwargs):
    self.processes=processes
    self.threshold=kwargs.get('threshold',None)
    self.aggregate=kwargs.get('aggregate',True)
    self.min_time=kwargs.get('min_time',3600)
    self.min_hosts=kwargs.get('min_hosts',1)    
    self.ignore_qs=kwargs.get('ignore_qs',['gpu','gpudev','vis',
                                           'visdev','development'])
    self.waynesses=kwargs.get('waynesses',[x+1 for x in range(32)])

    manager=multiprocessing.Manager()
    self.ratios=manager.dict()
    self.results=manager.dict()
    self.su=manager.dict()

  def setup(self,jobid):
    try:
      if self.aggregate:
        self.ts=tspl.TSPLSum(jobid,self.k1,self.k2)
      else:
        self.ts=tspl.TSPLBase(jobid,self.k1,self.k2)
    except tspl.TSPLException as e:
      return False
    except EOFError as e:
      print 'End of file found reading: ' + jobid
      return False

    if not tspl_utils.checkjob(self.ts,self.min_time,
                               self.waynesses,skip_queues=self.ignore_qs):
      return False
    elif self.ts.numhosts < self.min_hosts:
      return False
    else:
      return True

  def run(self,filelist):
    if not filelist: return 
    pool=multiprocessing.Pool(processes=self.processes) 
    pool.map(unwrap,zip([self]*len(filelist),filelist))
    pool.close()
    pool.join()

  def comp2thresh(self,jobid,val,func='>'):
    comp = {'>': operator.gt, '>=': operator.ge,
                '<': operator.le, '<=': operator.le,
                '==': operator.eq}
    self.su[self.ts.j.id] = (self.ts.owner,self.ts.su,val)
    if comp[func](val, self.threshold):
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

  def top_jobs(self, failed=True):
    jobs = {}
    if failed: jobs_list = self.failed()
    else: job_list = self.results.keys()

    total = {}

    for jobid in jobs_list:
      jobid = jobid.split('/')[-1]
      data = self.su[jobid]        
      if not data[0] in jobs: 
        jobs[data[0]] = []
        total[data[0]] = 0
      jobs[data[0]].append((jobid,data[1],data[2]))
      total[data[0]] += data[1]

    sorted_totals = sorted(total.iteritems(),key=operator.itemgetter(1))

    sorted_jobs = []
    for x in sorted_totals[::-1]:
      sorted_jobs.append((x,jobs[x[0]]))

    return sorted_jobs

  @abc.abstractmethod
  def test(self,jobid):
    """Run the test for a single job"""
    return

class MemBw(Test):

  k1=['intel_snb_imc', 'intel_snb_imc']
  k2=['CAS_READS', 'CAS_WRITES']

  def test(self,jobid):
    if not self.setup(jobid): return

    peak = 76.*1.e9
    gdramrate = numpy.zeros(len(self.ts.t)-1)
    for h in self.ts.j.hosts.keys():
      gdramrate += numpy.divide(numpy.diff(64.*self.ts.assemble([0,1],h,0)),
                                numpy.diff(self.ts.t))

    mdr=tmean(gdramrate)/self.ts.numhosts
    self.comp2thresh(jobid,mdr/peak)

    return

class Idle(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','LOAD_L1D_ALL','user'],}

  def test(self,jobid):
    if not self.setup(jobid): return

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
    self.comp2thresh(jobid,val)

    return

class Imbalance(Test):
  k1=None
  k2=None
  def __init__(self,k1=['intel_snb'],k2=['LOAD_L1D_ALL'],processes=1,aggregate=False,**kwargs):
    self.k1=k1
    self.k2=k2

    if aggregate:
      kwargs['min_hosts'] = 2
    kwargs['aggregate'] = aggregate
    kwargs['waynesses']=16
    super(Imbalance,self).__init__(processes=processes,**kwargs)

  def test(self,jobid):
    
    if not self.setup(jobid): return

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
      mean.append(tmean(vals[j]))
      std.append(tstd(vals[j]))

    imbl=maxval-minval

    self.ratio=numpy.divide(std,mean)
    self.ratio2=numpy.divide(imbl,maxval)

    # mean of ratios is the threshold statistic
    var=tmean(self.ratio) 
    self.ratios[self.ts.j.id]=[var,self.ts.owner]
    self.comp2thresh(jobid,abs(var))

  def find_top_users(self):
    users={}

    for k in self.ratios.keys():
      u=self.ratios[k][1]
      if not u in users:
        users[u]=[]
        users[u].append(0.)
        users[u].append([])
      else:
        users[u][0]=max(users[u][0],self.ratios[k][0])
        users[u][1].append(k)

    a=[ x[0] for x in sorted(users.iteritems(),
                             key=operator.itemgetter(1), reverse=True) ]
    maxi=len(a)+1
    maxi=min(10,maxi)
    print '---------top 10----------'
    for u in a[0:maxi]:
      print u + ' ' + str(users[u][0]) + ' ' + ' '.join(users[u][1])
    return users

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
    if not self.setup(jobid): return 

    bad_hosts=tspl_utils.lost_data(self.ts)
    if len(bad_hosts) > 0:
      print self.ts.j.id, ': Detected hosts with bad data: ', bad_hosts
      return

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
      self.comp2thresh(jobid,ratio,'<')
      if self.results[jobid]: break

    return

class LowFLOPS(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL','user'],}

  peak={'amd64' : [2.3e9*16*2, 24e9, 1.],
        'intel_snb' : [ 16*2.7e9*2, 16*2.7e9/2.*64., 1.],}
  
  def test(self,jobid):
    if not self.setup(jobid): return

    ts=self.ts
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
        
    mfr=tmean(gfloprate)/ts.numhosts
    mdr=tmean(gdramrate)/ts.numhosts
    mcr=tmean(gcpurate)/(ts.numhosts*ts.wayness*100.)
    if (mcr/self.peak[ts.pmc_type][2] > 0.5):
      self.comp2thresh(jobid,(mfr/self.peak[ts.pmc_type][0])/(mdr/self.peak[ts.pmc_type][1]),'<')
    else: self.results[jobid]=False

    return


class MetaDataRate(Test):
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

  def test(self,jobid):
    if not self.setup(jobid): return
    ts = self.ts

    if not tspl_utils.checkjob(ts,self.min_time,range(1,33)): return
    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    meta_rate = numpy.zeros_like(tmid)

    for k in ts.j.hosts.keys():
      meta_rate+=numpy.diff(ts.assemble(range(0,len(self.k1)),k,0))/numpy.diff(ts.t)

    meta_rate  /= float(ts.numhosts)
    
    self.comp2thresh(jobid,numpy.max(meta_rate))

    return  
    
class HighCPI(Test):
  k1 = ['intel_snb', 'intel_snb']      
  k2 = ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED' ]

  def test(self,jobid):
    if not self.setup(jobid): return
    ts = self.ts

    if "FAIL" in ts.status: return
    if "CANCELLED" in ts.status: return  

    tmid=(ts.t[:-1]+ts.t[1:])/2.0       
    clock_rate = numpy.zeros_like(tmid)
    instr_rate = numpy.zeros_like(tmid)
    for k in ts.j.hosts.keys():
      clock_rate += numpy.diff(ts.assemble([0],k,0))/numpy.diff(ts.t)
      instr_rate += numpy.diff(ts.assemble([1],k,0))/numpy.diff(ts.t)

    cpi = tmean(clock_rate/instr_rate)

    self.comp2thresh(jobid,cpi)

class HighCPLD(Test):
  k1 = ['intel_snb', 'intel_snb']      
  k2 = ['CLOCKS_UNHALTED_REF','LOAD_L1D_ALL' ]

  def test(self,jobid):
    if not self.setup(jobid): return
    ts = self.ts

    if "FAIL" in ts.status: return
    if "CANCELLED" in ts.status: return  

    tmid=(ts.t[:-1]+ts.t[1:])/2.0       
    clock_rate = numpy.zeros_like(tmid)
    instr_rate = numpy.zeros_like(tmid)
    for k in ts.j.hosts.keys():
      clock_rate += numpy.diff(ts.assemble([0],k,0))/numpy.diff(ts.t)
      instr_rate += numpy.diff(ts.assemble([1],k,0))/numpy.diff(ts.t)

    cpi = tmean(clock_rate/instr_rate)

    self.comp2thresh(jobid,cpi)
       
