import cPickle as pickle
import numpy,pwd
import glob, os, stat, time, datetime, sys
import re
import tspl_utils
import math
import logging, multiprocessing
from tacc_stats.pickler import job_stats, batch_acct
sys.modules['job_stats'] = job_stats
sys.modules['batch_acct'] = batch_acct
sys.modules['pickler.job_stats'] = job_stats
sys.modules['pickler.batch_acct'] = batch_acct

VERBOSE=False
class TSPLException(Exception):
  def __init__(self,arg):
    self.value=arg
    print self.value

class TSPLBase:
  def __init__(self,file,k1,k2,job_data = None):

    if job_data:
      self.j = job_data
    else:
      self.f=open(file)
      try:
        self.j=pickle.load(self.f)
      except EOFError as e:
        raise TSPLException('End of file found for: ' + file)
      self.f.close()
    
    try:
      self.queue=self.j.acct['queue']
    except KeyError:
      print 'No queue found'
      self.queue = None

    self.status='Unknown'
    try:
      self.status=self.j.acct['status']
    except KeyError:
      try:
        self.status=self.j.acct['exit_status']
      except KeyError as e:
        pass
      pass

    try:
      self.owner=pwd.getpwuid(int(self.j.acct['uid']))[0]
    except KeyError:
      try:
        self.owner=self.j.acct['owner']
      except Exception as e:
        self.owner=self.j.acct['uid']        
    except Exception as e:
      self.owner=self.j.acct['uid']
      
    self.numhosts=len(self.j.hosts.keys())

    if self.numhosts == 0:
      raise TSPLException('No hosts in job '+ str(self.j.id))


    if 'amd64_core' in self.j.hosts.values()[0].stats:
      self.pmc_type='amd64'
    elif 'intel_pmc3' in self.j.hosts.values()[0].stats:
      self.pmc_type='intel_pmc3'
    elif 'intel_nhm' in self.j.hosts.values()[0].stats:
      self.pmc_type='intel_nhm'
    elif 'intel_wtm' in self.j.hosts.values()[0].stats:
      self.pmc_type='intel_wtm'
    elif 'intel_snb' in self.j.hosts.values()[0].stats:
      self.pmc_type='intel_snb'
    elif 'intel_hsw' in self.j.hosts.values()[0].stats:
      self.pmc_type='intel_hsw'

    default_wayness = {"amd64_cores" : 4, "intel_pmc3" : 8, "intel_nhm" : 12, 
                       "intel_wtm" : 12, "intel_snb" : 16, "intel_hsw" : 24}

    try: 
      self.wayness=int(self.j.acct['cores'])/int(self.j.acct['nodes'])
    except ZeroDivisionError:
      if VERBOSE: print "Read zero nodes, assuming 16 way for job " + str(self.j.id)
      self.wayness=default_wayness[self.pmc_type]
    except KeyError:
      try:
        self.wayness=int(re.findall('\d+',self.j.acct['granted_pe'])[0])
      except AttributeError:
        raise TSPLException("Pickle file broken: " + file)
    except TypeError:
      raise TSPLException('Something is funny with job ' +str(self.j.id) +
                            ' ' + str(self.j.acct['cores']) + ' ' +
                            str(self.j.acct['nodes']))
    except:
      raise TSPLException('Something is funny with file' + file )


    if isinstance(k1,dict) and isinstance(k2,dict):
      
      if self.pmc_type in k1:
        self.k1=k1[self.pmc_type]
        self.k2=k2[self.pmc_type]
      
      if not self.k1[0] in self.j.schemas:
        raise TSPLException(self.k1[0]+' not supported for job '+str(self.j.id))

    elif isinstance(k1,list) and isinstance(k2,list):
      self.k1=k1
      self.k2=k2
      
      if not self.k1[0] in self.j.schemas:
        raise TSPLException(self.k1[0]+' not supported for job '+str(self.j.id))      
    else:
      raise TSPLException('Input types must match and be lists or dicts: ' +
                          str(type(k1)) + ' ' + str(type(k2)))

    try:
      self.t=(self.j.times-self.j.times[0])
    except:
      raise TSPLException('Time series is '+str(self.j.times))
    

    if len(self.t) == 0:
      raise TSPLException('Time range is 0')

    if len(k1) != len(k2):
      raise TSPLException('Lengths don\'t match')

    self.index=[]

    for i in range(len(self.k1)):
      if self.k1[i] in self.j.schemas and \
      self.k2[i] in self.j.schemas[self.k1[i]]:
        self.index +=  [self.j.get_schema(self.k1[i])[self.k2[i]].index]
      else:
        self.index += [-1]

###    self.index=[ self.j.get_schema(self.k1[i])[self.k2[i]].index
###                 for i in range(len(self.k1))]

    g=self.j.hosts[self.j.hosts.keys()[0]]
    self.size=len(g.stats[self.k1[0]].values()[0])

    d=datetime.datetime.fromtimestamp(self.j.acct['start_time'])
    self.start_date=d.strftime('%Y-%m-%d %H:%M:%S')
    d=datetime.datetime.fromtimestamp(self.j.acct['end_time'])
    self.end_date=d.strftime('%Y-%m-%d %H:%M:%S')

    self.title='ID: %(ID)s, u: %(u)s, q: %(queue)s, N: %(name)s, '\
                'D: %(date)s, NH: %(nh)d' % \
           { 'ID' : self.j.id,'u': self.owner, 'queue': self.queue,
             'name': tspl_utils.string_shorten(self.j.acct['name'],15),
             'nh' : self.numhosts,
             'date': self.end_date }

    # Create an array of dictionaries of lists initialized and constructed using
    # derived class methods for the keys of interest.
    # self.index embedds the location of self.k2 in the sechma
    try:
      self.data=[]
      for i in range(len(self.k1)):
        self.data.append({})
        for k in self.j.hosts.keys():
          h=self.j.hosts[k]
          self.data[i][k]=self.data_init()
          try:
            for s in h.stats[self.k1[i]].values():
              self.data_assign(self.data[i][k],s[:,self.index[i]])
          except KeyError:
            continue
            
    except Exception as e:
      exc_type, exc_obj, exc_tb = sys.exc_info()
      fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
      if VERBOSE: print(exc_type, fname, exc_tb.tb_lineno)
      
  # Initialize to an empty array and accumulate with appending
  def data_init(self):
    return []
  def data_assign(self,d,v):
    d.append(numpy.array(v,dtype=numpy.float))

  # Generate a label for title strings
  def label(self,k1,k2,mod=1.):
    u=''
    if mod==1e9 or mod == 1024.**3:
      u='G'
    elif mod==1e6 or mod == 1024.**2:
      u='M'

    l=k1 + ' ' + k2
    if k2 in self.j.get_schema(k1):
      s=self.j.get_schema(k1)[k2]
      if not s.unit is None:
        l+=' ' + u + s.unit

    if len(l) > 10:
      l=k1 + '\n' + k2
      if k2 in self.j.get_schema(k1):
        s=self.j.get_schema(k1)[k2]
        if not s.unit is None:
          l+=' ' + u + s.unit
      
    return l
      
  # These iterator fuctions iterate linearly over the array of dictionaries. We
  # should probably create a sorted version, but this works for now.
  def __iter__(self):
    self.ind=-1
    self.a=len(self.data)
    self.b=len(self.data[0].keys())
    self.c=len(self.data[0][self.data[0].keys()[0]])

    return(self)

  def next(self):
    if self.ind == self.a*self.b*self.c-1:
      raise StopIteration
    self.ind += 1
    inds=numpy.unravel_index(self.ind,(self.a,self.b,self.c))
    k=self.data[inds[0]].keys()[inds[1]]
    return self.data[inds[0]][k][inds[2]]

  # Return a numpy array that accumulates from data using the indices of the
  # loaded keys. Negative indices subtract.
  # jndex should always be 0 for TSPLSum objects, but allows selecting over
  # device indices when a TSPLBase object is used (refactor to default this?)
  
  def assemble(self,index,host,jndex):
    data=self.data
    v=numpy.zeros_like(data[0][host][jndex])
    for i in index:
      i2=abs(i)
      v+=math.copysign(1,i)*data[i2][host][jndex]
    return v


#  units_correction={
#    ('intel_snb_imc','CAS_READS') : 
#    }

# Load a job file and sum a socket-based or core-based counter into
# time-dependent arrays for each key pair. Takes a tacc stats pickle file and
# two lists of keys. 

class TSPLSum(TSPLBase):
  def __init__(self,file,k1,k2, job_data = None):
    TSPLBase.__init__(self, file, k1, k2, job_data = job_data)

  # Initialize with an zero array and accumuluate to the first list element with
  # a sum
  def data_init(self):
    return [numpy.zeros(self.size)]
  def data_assign(self,d,v):
    d[0]+=v
  
