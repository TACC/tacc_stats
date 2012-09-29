import cPickle as pickle
import numpy
import glob, os, stat, time
import re

class TSPLException(Exception):
  def __init__(self,arg):
    self.value=arg
    print self.value

class TSPLBase:
  def __init__(self,file,k1,k2):
    self.f=open(file)
    self.j=pickle.load(self.f)
    self.f.close()
    self.wayness=int(re.findall('\d+',self.j.acct['granted_pe'])[0])
    self.numhosts=len(self.j.hosts.keys())

    if self.numhosts == 0:
      raise TSPLException('No hosts')
    elif not 'amd64_core' in self.j.hosts.values()[0].stats:
      raise TSPLException('No PMC data for: ' + self.j.id)
        
    self.k1=k1
    self.k2=k2

    self.t=(self.j.times-self.j.times[0])

    if len(k1) != len(k2):
      raise TSPLException('Lengths don\'t match')

    self.index=[ self.j.get_schema(self.k1[i])[self.k2[i]].index
                 for i in range(len(self.k1))]

    g=self.j.hosts[self.j.hosts.keys()[0]]
    self.size=len(g.stats[self.k1[0]].values()[0])

    self.title='ID: %(ID)s, user: %(u)s, N: %(name)s, NH: %(nh)d' % \
           { 'ID' : self.j.id,'u': self.j.acct['owner'],
             'name': self.j.acct['name'], 'nh' : self.numhosts }

    # Create an array of dictionaries of lists initialized and constructed using
    # derived class methods for the keys of interest.
    # self.index embedds the location of self.k2 in the sechma
    self.data=[]
    for i in range(len(self.k1)):
      self.data.append({})
      for k in self.j.hosts.keys():
        h=self.j.hosts[k]
        self.data[i][k]=self.data_init()
        for s in h.stats[self.k1[i]].values():
          self.data_assign(self.data[i][k],s[:,self.index[i]])

  # Initialize to an empty array and accumulate with appending
  def data_init(self):
    return []
  def data_assign(self,d,v):
    d.append(v)

  # Generate a label for title strings
  def label(self,k1,k2):
    l=k1 + ' ' + k2
    s=self.j.get_schema(k1)[k2]
    if not s.unit is None:
      l+=' ' + s.unit
      
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

# Load a job file and sum a socket-based or core-based counter into
# time-dependent arrays for each key pair. Takes a tacc stats pickle file and
# two lists of keys. 

class TSPickleLoader(TSPLBase):
  def __init__(self,file,k1,k2):
    TSPLBase.__init__(self,file,k1,k2)

  # Initialize with an zero array and accumuluate to the first list element with
  # a sum
  def data_init(self):
    return [numpy.zeros(self.size)]
  def data_assign(self,d,v):
    d[0]+=v
  
# Check a TSPickleLoader object to see if its job has a minimum run time and has
# its wayness in a list
def checkjob(ts, minlen, way):
  if ts.t[len(ts.t)-1] < minlen:
    print ts.j.id + ': %(time)8.3f' % {'time' : ts.t[len(ts.t)-1]/3600} \
          + ' hours'
    return False
  elif getattr(way, '__iter__', False):
    if ts.wayness not in way:
      print ts.j.id + ': skipping ' + str(ts.wayness) + '-way'
      return False
  elif ts.wayness != way:
    print ts.j.id + ': skipping ' + str(ts.wayness) + '-way'
    return False
  return True

# Generate a list of files from a command line arg. If filearg is a glob
# pattern, glob it, if it's a directory, then add '/*' and glob that, otherwise
# treat it as a single file and return a list of that
    
def getfilelist(filearg):
  filelist=glob.glob(filearg)
  if len(filelist)==1:
    mode=os.stat(filearg).st_mode
    if stat.S_ISDIR(mode):
      filelist=glob.glob(filearg+'/*')
    else:
      filelist=[filearg]
  return filelist

# Center, expand, and decenter a range

def expand_range(xmin,xmax,factor):
  xc=(xmin+xmax)/2.
  return [(xmin-xc)*(1.+factor)+xc,
          (xmax-xc)*(1.+factor)+xc]
