from __future__ import print_function
import os,sys
import abc
import operator,traceback
import multiprocessing
from datetime import date
from tacc_stats.analysis.gen import tspl,tspl_utils

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

  # '>' If metric is greater than threshold flag the job 
  # '<' If metric is less than threshold flag the job 
  @abc.abstractproperty
  def comp_operator(self): pass

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
    self.results=manager.dict()

  def setup(self,job_path,job_data=None):
    self.metric = float("nan")
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
    if not filelist: 
      print("Please specify a job file list.")
      return 

    pool=multiprocessing.Pool(processes=self.processes) 
    pool.map(unwrap,zip([self]*len(filelist),filelist,[kwargs]*len(filelist)))
    pool.close()
    pool.join()

  comp = {'>': operator.gt, '>=': operator.ge,
          '<': operator.le, '<=': operator.le,
          '==': operator.eq}

  def failed(self):
    jobs=[]
    for i in self.results.keys():
      if self.results[i]['result']:
        jobs.append(i)
    return jobs

  # Report top users by SU usage, only count failed jobs 
  # by default
  def top_jobs(self, failed=True):
    jobs = {}
    total = {}

    if failed: jobs_list = self.failed()
    else: job_list = self.results.keys()

    for jobid in jobs_list:
      data = self.results[jobid]        
      owner = data['owner']

      jobs.setdefault(owner,[]).append([jobid,data['su'],data['metric'],data['result']])
      total[owner] = total.get(owner,0) + data['su']

    sorted_totals = sorted(total.iteritems(),key=operator.itemgetter(1))
    sorted_jobs = []
    for x in sorted_totals[::-1]:
      sorted_jobs.append((x,jobs[x[0]]))

    return sorted_jobs

  def date_sweep(self,start,end,directory=None):
    if not directory: return

    for date_dir in os.listdir(directory):

      try:
        s = [int(x) for x in start.split('-')]
        e = [int(x) for x in end.split('-')]
        d = [int(x) for x in date_dir.split('-')]
      except: continue

      if not date(s[0],s[1],s[2]) <= date(d[0],d[1],d[2]) <= date(e[0],e[1],e[2]): 
        continue

      print('>>>',date_dir)
      files = os.path.join(directory,date_dir)

    filelist=tspl_utils.getfilelist(files)
    self.run(filelist)
      
    passed = 0
    failed = 0

    for data in self.results.values():
      if data['result']: passed +=1
      else: failed += 1

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
  def compute_metric(self):
    pass
    """Compute metric of interest"""

  def comp2thresh(self):
    return

  def test(self,job_path,job_data=None):
    # Setup job data and filter out unwanted jobs
    if not self.setup(job_path,job_data=job_data): return

    # Compute metric of interest
    self.compute_metric()

    # Compare metric to threshold and record result
    val = self.comp[self.comp_operator](self.metric, self.threshold)
    self.results[self.ts.j.id] = {'owner' : self.ts.owner,
                                  'su' : self.ts.su,
                                  'metric' : self.metric,
                                  'result' : val
                                  }

    """Run the test for a single job, comparing threshold
    to metric"""
    return



       
