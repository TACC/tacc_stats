import cPickle as pickle
import numpy
import glob, os, stat, time
import re

class TSPLException(Exception):
  def __init__(self,arg):
    self.value=arg
    print arg

class TSPLBase:
  def __init__(self,file,k1,k2):
    self.f=open(file)
    self.j=pickle.load(self.f)
    self.f.close()
    self.wayness=int(re.findall('\d+',self.j.acct['granted_pe'])[0])
    self.numhosts=len(self.j.hosts.keys())
    
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

  # These iterator fuctions iterate linearly over the array of dictionaries. We
  # should probably create a sorted version, but this works for now.
  def __iter__(self):
    self.ind=-1
    self.maxi=len(self.k1)*len(self.j.hosts.keys())
    return(self)

  def next(self):
    if self.ind == self.maxi-1:
      raise StopIteration
    self.ind += 1

    x=self.ind/len(self.k1)
    y=self.ind - x*len(self.k1)
    k=self.j.hosts.keys()[x]

    return self.data[y][k]

# Load a job file and sum a socket-based or core-based counter into
# time-dependent arrays for each key pair. Takes a tacc stats pickle file and
# two lists of keys. 

class TSPickleLoader(TSPLBase):
  def __init__(self,file,k1,k2):
    TSPLBase.__init__(self,file,k1,k2)

    # Array of dictionaries giving the sum of each key pair for each
    # host. Dictionary key is the hostname. self.index embedds the location of
    # self.k2 in the sechma
    self.data=[]
    for i in range(len(self.k1)):
      self.data.append({})
      for k in self.j.hosts.keys():
        h=self.j.hosts[k]
        self.data[i][k]=numpy.zeros(self.size)
        for s in h.stats[self.k1[i]].values():
          self.data[i][k]+=s[:,self.index[i]]

## Same, but doesn't sum anything.
class TSPickleLoaderFull(TSPLBase):
  def __init__(self,file,k1,k2):
    TSPLBase.__init__(self,file,k1,k2)

    # Create an array of dictionaries  containing all the arrays for all the
    # keys of interest. self.index embedds the location of self.k2 in the sechma
    self.data=[]
    for i in range(len(self.k1)):
      self.data.append({})
      for k in self.j.hosts.keys():
        h=self.j.hosts[k]
        for s in h.stats[self.k1[i]].values():
          self.data[i][k]=s[:,self.index[i]]

  
# Check a TSPickleLoader object to see if its job has a minimum run time and has
# its wayness in a list
def checkjob(ts, minlen, way):
  if ts.t[len(ts.t)-1] < minlen:
    print ts.j.id + ': %(time)8.3f' % {'time' : ts.t[len(ts.t)-1]/3600} \
          + ' hours'
    return False
  elif getattr(way, '__iter__', False):
    if ts.wayness not in way:
      print ts.j.id + ': skipping ' + str(ts.wayness)
      return False
  elif ts.wayness != way:
    print ts.j.id + ': skipping ' + str(ts.wayness)
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
