from __future__ import print_function
import os,sys
import abc
import operator,traceback
import multiprocessing
from datetime import date
from tacc_stats.analysis.gen import tspl,tspl_utils
import tacc_stats.cfg as cfg

def unwrap(args):
  try:
    return args[0].test(args[1],**args[2])
  except:
    print(traceback.format_exc())
    pass

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

  def setup(self,jobid,job_data=None):
    self.metric = float("nan")
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

    if "FAIL" in self.ts.status: return False
    if "CANCELLED" in self.ts.status: return False 

    if not tspl_utils.checkjob(self.ts,self.min_time,
                               self.waynesses,skip_queues=self.ignore_qs):
      return False
    elif self.ts.numhosts < self.min_hosts:
      return False
    else:
      return True

  def run(self,filelist,**kwargs):
    if not filelist: return 
    pool=multiprocessing.Pool(processes=self.processes) 
    pool.map(unwrap,zip([self]*len(filelist),filelist,[kwargs]*len(filelist)))
    pool.close()
    pool.join()

  def comp2thresh(self,jobid,val,func='>'):
    comp = {'>': operator.gt, '>=': operator.ge,
                '<': operator.le, '<=': operator.le,
                '==': operator.eq}
    self.metric = val
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

  def date_sweep(self,start,end):
    for date_dir in os.listdir(cfg.pickles_dir):

      try:
        s = [int(x) for x in start.split('-')]
        e = [int(x) for x in end.split('-')]
        d = [int(x) for x in date_dir.split('-')]
      except: continue

      if not date(s[0],s[1],s[2]) <= date(d[0],d[1],d[2]) <= date(e[0],e[1],e[2]): 
        continue

      print('>>>',date_dir)
      files = os.path.join(cfg.pickles_dir,date)

    filelist=tspl_utils.getfilelist(files)
    self.run(filelist)
      
    passed = self.results.values().count(True)
    failed = self.results.values().count(False)
    total = passed + failed

    print("---------------------------------------------")
    try: 
      print("Jobs tested:",passed+failed)
      print("Percentage of jobs failed:",100*passed/float(total))
    except ZeroDivisionError: 
      print("No jobs failed.")
      return
    print('Failed jobs')
    for x in self.top_jobs():
      print(x[0],x[1])
    return self.failed()

  @abc.abstractmethod
  def test(self,jobid,job_data=None):
    """Run the test for a single job"""
    return


       
