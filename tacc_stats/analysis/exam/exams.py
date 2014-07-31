from __future__ import print_function
import os,sys
import abc
import operator,traceback
import multiprocessing
from datetime import datetime,timedelta
from tacc_stats.analysis.gen import tspl,tspl_utils
from scipy.stats import tmean

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
    self.ignore_status=kwargs.get('ignore_status',[])
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

    if self.ts.status in self.ignore_status: return False
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
        jobs.append(self.results[i]['job_path'])
    return jobs

  # Report top users by SU usage, only count failed jobs 
  # by default
  def top_jobs(self, failed=True):
    jobs = {}
    total = {}
    
    job_list = []
    for jobid in self.results.keys():
      if self.results[jobid]['result']: job_list.append(jobid)

    for jobid in job_list:
      data = self.results[jobid]        
      owner = data['owner']

      jobs.setdefault(owner,[]).append([jobid,data['su'],data['metric'],data['result']])
      total[owner] = total.get(owner,0) + data['su']

    sorted_totals = sorted(total.iteritems(),key=operator.itemgetter(1))
    sorted_jobs = []
    for x in sorted_totals[::-1]:
      sorted_jobs.append((x,jobs[x[0]]))

    return sorted_jobs

  def date_sweep(self,start,end,pickles_dir=None):
    try:
      start = datetime.strptime(start,"%Y-%m-%d")
      end   = datetime.strptime(end,"%Y-%m-%d")
    except:
      start = datetime.now() - timedelta(days=1)
      end   = start

    filelist = []
    for root,dirnames,filenames in os.walk(pickles_dir):
      for directory in dirnames:

        date = datetime.strptime(directory,'%Y-%m-%d')
        if max(date.date(),start.date()) > min(date.date(),end.date()): continue

        print('for date',date.date())
        filelist.extend(tspl_utils.getfilelist(os.path.join(root,directory)))
      break

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

  def arc(self,data):
    avg = 0
    self.val = {}
    for h in self.ts.j.hosts.keys():
      self.val[h] = (data[h][0][-1]-data[h][0][0])*(self.ts.t[-1]-self.ts.t[0])**-1
      avg += (data[h][0][-1]-data[h][0][0])*(self.ts.t[-1]-self.ts.t[0])**-1

    return avg/self.ts.numhosts

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
                                  'result' : val,
                                  'job_path' : job_path
                                  }

    """Run the test for a single job, comparing threshold
    to metric"""
    return



       
