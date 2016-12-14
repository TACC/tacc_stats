from __future__ import print_function
import sys
import abc
import operator,traceback
import cPickle as pickle
import multiprocessing
from tacc_stats.analysis.gen import tspl,tspl_utils

def _unwrap(args):
  try:
    return args[0].get_measurements(args[1])
  except Exception as e:
    print(traceback.format_exc())
    #raise e
    pass

class Auditor():

  comp = {'>': operator.gt, '>=': operator.ge,
          '<': operator.le, '<=': operator.le,
          '==': operator.eq}

  def __init__(self, processes = 4, **kwargs):
    self.processes = processes
    self.metrics = {}
    self.results = {}
    self.measures = {}    

  def stage(self, Measure, **kwargs):
    self.measures[Measure.__name__] = Measure(**kwargs)

  # Compute metrics in parallel (Shared memory only)
  def run(self, filelist):
    if not filelist: 
      print("Please specify a job file list.")
      sys.exit()
    #pool = multiprocessing.Pool(processes=self.processes) 
    #metrics = pool.map(_unwrap, zip([self]*len(filelist), filelist))
    metrics = map(_unwrap, zip([self]*len(filelist), filelist))
    
    for d in metrics:
      if not d: continue
      for metric_name, job in d.iteritems():
        self.metrics.setdefault(metric_name, {}) 
        self.metrics[metric_name][job[0]] = job[1]
    
  # Compute metric
  def get_measurements(self,jobpath):
    try:
      with open(jobpath) as fd:
        job_data = pickle.load(fd)
    except IOError as e:
      raise tspl.TSPLException('File ' + jobpath + ' not found')
    except EOFError as e:
      raise tspl.TSPLException('End of file found for: ' + jobpath)

    metrics = {}
    for name, measure in self.measures.iteritems():
      print (name)
      metrics[name] = (job_data.id, measure.test(jobpath,job_data))
    return metrics

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
    self.waynesses=kwargs.get('waynesses',[x+1 for x in range(64)])
    self.ignore_status=kwargs.get('ignore_status',[])

  # Sets up particular combination of events and filters
  def setup(self,job_path,job_data=None):
    
    try:
      if self.aggregate:
        self.ts=tspl.TSPLSum(job_path,self.k1,self.k2,job_data=job_data)
      else:
        self.ts=tspl.TSPLBase(job_path,self.k1,self.k2,job_data=job_data)
    except tspl.TSPLException as e:
      print(sys.exc_info()[0])
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
    avg = 0.0
    self.val = {}
    idt = (self.ts.t[-1]-self.ts.t[0])**-1
    for h in self.ts.j.hosts.keys():
      self.val[h] = (data[h][0][-1]-data[h][0][0])*idt
      avg += self.val[h]
    return avg/self.ts.numhosts

  def test(self,jobpath,job_data):
    # Setup job data and filter out unwanted jobs
    if not self.setup(jobpath,job_data=job_data): return
    
    # Compute metric of interest
    try:
      self.compute_metric()
    except: pass

    return self.metric



       
