from __future__ import print_function
import sys
import abc
import operator,traceback
import cPickle as pickle
import multiprocessing
from tacc_stats.analysis.gen import tspl,tspl_utils

def unwrap(args):
  try:
    return args[0].get_measurements(args[1],**args[2])
  except:
    print(traceback.format_exc())
    pass

class Auditor():

  comp = {'>': operator.gt, '>=': operator.ge,
          '<': operator.le, '<=': operator.le,
          '==': operator.eq}

  def __init__(self, processes=1, **kwargs):
    self.processes = processes
    self.metrics = {}
    self.results = {}
    self.measures = {}
    manager = multiprocessing.Manager()
    self.accts = manager.dict()
    self.paths = manager.dict()

  def stage(self, Measure, **kwargs):
    self.measures[Measure.__name__] = Measure(**kwargs)
    manager = multiprocessing.Manager()
    self.metrics[Measure.__name__] = manager.dict()

  # Compute metrics in parallel (Shared memory only)
  def run(self, filelist, **kwargs):
    if not filelist: 
      print("Please specify a job file list.")
      sys.exit()
    pool = multiprocessing.Pool(processes=self.processes) 
    pool.map(unwrap,zip([self]*len(filelist),filelist,[kwargs]*len(filelist)))
    pool.close()
    pool.join()

  # Compute metric
  def get_measurements(self,jobpath):
    with open(jobpath) as fd:
      try:
        job_data = pickle.load(fd)
        self.accts[job_data.id] = job_data.acct
        self.paths[job_data.id] = jobpath
      except EOFError as e:
        raise TSPLException('End of file found for: ' + jobpath)

    for name, measure in self.measures.iteritems():
      self.metrics[name][job_data.id] = measure.test(jobpath,job_data)

  # Compare metric to threshold
  def test(self, Measure, threshold = 1.0):
    self.results[Measure.__name__] ={}
    for jobid in self.metrics[Measure.__name__].keys():
      self.results[Measure.__name__][jobid] = None
      if self.metrics[Measure.__name__][jobid]:
        self.results[Measure.__name__][jobid] = self.comp[Measure.comp_operator](self.metrics[Measure.__name__][jobid], threshold)
    
  

class Test(object):
  __metaclass__ = abc.ABCMeta

  @abc.abstractproperty
  def k1(self): pass
  @abc.abstractproperty
  def k2(self): pass

  # '>' If metric is greater than threshold flag the job 
  # '<' If metric is less than threshold flag the job 
  @abc.abstractproperty
  def comp_operator(self): pass
  
  ts = None
  metric = None
  
  # Provide filters here
  def __init__(self,processes=1,**kwargs):
    self.processes=processes
    self.aggregate=kwargs.get('aggregate',True)
    self.min_time=kwargs.get('min_time',3600)
    self.min_hosts=kwargs.get('min_hosts',1)    
    self.ignore_qs=kwargs.get('ignore_qs',['gpu','gpudev','vis','visdev','development'])
    self.waynesses=kwargs.get('waynesses',[x+1 for x in range(32)])
    self.ignore_status=kwargs.get('ignore_status',[])

  # Sets up particular combination of events and filters
  def setup(self,job_path,job_data=None):
    try:
      if self.aggregate:
        self.ts=tspl.TSPLSum(job_path,self.k1,self.k2,job_data=job_data)
      else:
        self.ts=tspl.TSPLBase(job_path,self.k1,self.k2,job_data=job_data)
    except tspl.TSPLException as e:
      return False
    except EOFError as e:
      print('End of file found reading: ' + job_path)
      return False
    
    return tspl_utils.checkjob(self.ts,
                               self.min_time,
                               self.min_hosts,
                               self.waynesses,
                               skip_queues=self.ignore_qs,
                               ignore_status=self.ignore_status)

  @abc.abstractmethod
  def compute_metric(self):
    pass
    """Compute metric of interest"""

  # Compute Average Rate of Change
  def arc(self,data):
    avg = 0
    self.val = {}
    idt = (self.ts.t[-1]-self.ts.t[0])**-1
    for h in self.ts.j.hosts.keys():
      self.val[h] = (data[h][0][-1]-data[h][0][0])*idt
      avg += self.val[h]
    return avg/self.ts.numhosts

  def test(self,jobpath,job_data):
    # Setup job data and filter out unwanted jobs
    print(jobpath,job_data)
    if not self.setup(jobpath,job_data=job_data): return
    # Compute metric of interest
    self.compute_metric()
    return self.metric



       
