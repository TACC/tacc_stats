import json
import time, os, fnmatch
import re
import textwrap

def make_date_string(t):
  lt=time.localtime(t)
  return '%(y)04d-%(m)02d-%(d)02d' % { 'y' : lt.tm_year, 'm' : lt.tm_mon,
                                       'd' : lt.tm_mday }
def replace_path_bits(path,user,maxlen):
  res=re.sub('/work/[0-9]+/'+user,r'\$WORK',path)
  res=re.sub('/scratch/[0-9]+/'+user,r'\$SCRATCH',res)
  res=re.sub('.*?/home.*?/[0-9]+/'+user,'~'+user,res)
  return res

def replace_and_shorten_path_bits(path,user,maxlen):
  res=replace_path_bits(path,user,maxlen)
  if len(res) > maxlen:
    res=re.sub(r'/[^/][^/]*/..*/(..*/)',r'/.../\1',res)
  return res

def replace_and_wrap_path_bits(path,user,maxlen,indent=0):
  res=replace_path_bits(path,user,maxlen)
  if len(res) < maxlen:
    return res
  wrapped=textwrap.wrap(' '.join(res.split('/')),maxlen)
  res=''
  for i in range(len(wrapped)-1):
    res += '/'.join(wrapped[i].split(' ')) + '/\n' + (' '*indent)
  res+='/'.join(wrapped[-1].split(' '))

  return res

class LariatDataException(Exception):
  def __init__(self,arg):
    self.value=arg
    print self.value

class LariatData:
  def __init__(self,jobid,end_epoch=-1,directory=None,daysback=0,olddata=None):

    self.jobid=jobid

    # Initialize to invalid/empty states
    self.id=0
    self.ld=None
    self.user='nobody'
    self.exc='unknown'
    self.cwd='unknown'
    self.threads=1
    self.wayness=-1


    # Find the set of JSON files matching the end_epoch date
    newdata=None
    if end_epoch > 0 and directory != None:
      matches=[]
      for day in range(daysback+1):
        ds=make_date_string(end_epoch-day*24*3600)
        for root, dirnames, filenames in os.walk(directory):
          for fn in fnmatch.filter(filenames,'*'+ds+'.json'):
            matches.append(os.path.join(root,fn))
      if len(matches) != 0:
        newdata=dict()
        for m in matches:
          try:
            newdata.update(json.load(open(m))) # Should be only one match
          except:
            json_str = open(m).read()
            json_str = re.sub(r'\\','',json_str)
            newdata.update(json.loads(json_str))
      else:
        print 'File for ' + self.jobid + ' not found in ' + directory

    if olddata != None:
      self.ld=olddata
    else:
      self.ld=dict()
    if newdata != None:
      self.ld.update(newdata)

    try:
      self.ld[jobid].sort(key=lambda ibr: int(ibr['startEpoch']))
      self.id=self.ld[jobid][0]['jobID']
      self.user=self.ld[jobid][0]['user']
      self.exc=replace_and_shorten_path_bits(self.ld[jobid][0]['exec'],
                                             self.user,60)
      self.cwd=replace_and_shorten_path_bits(self.ld[jobid][0]['cwd'],
                                             self.user,60)
      self.threads=self.ld[jobid][0]['numThreads']
      self.wayness=int(self.ld[jobid][0]['numCores'])/int(self.ld[jobid][0]['numNodes'])
    except KeyError:
      print str(jobid) + ' did not call ibrun' + \
            ' or has no lariat data for some other reason'

    self.equiv_patterns = {
      r'^charmrun' : 'Charm++*',
      r'^wrf' : 'WRF*',
      r'^vasp' : 'VASP*',
      r'^run\.cctm' : 'CMAQ CCTM*',
      r'^lmp_' : 'LAMMPS*',
      r'^mdrun' : 'Gromacs*',
      r'^enzo' : 'ENZO*',
      r'^dlpoly' : 'DL_POLY*',
      r'^su3_' : 'MILC*',
      r'^qcprog' : 'QCHEM*',
      r'^namd2' : 'NAMD*',
      r'^cactus' : 'Cactus*',
      r'^pw.x' : 'Q. Esp*',
      r'^pmemd' : 'Amber*',
      r'^sander' : 'Amber*',
      r'^charmm' : 'CHARMM*',
      r'^c37b1'  : 'CHARMM*',
      }
    
  def title(self):
    title='E: ' + self.exc
    if (self.cwd != 'unknown'):
      if ((len(self.exc) + len (self.cwd)) > 50):
        sep=',\n'
      else:
        sep=', '
      title += sep + 'CWD: ' + self.cwd
    return title
  
  def comp_name(self,name,patterns):
    for i in patterns.keys():
      if re.search(i,name):
        return patterns[i]
    return name

  def get_runtimes(self,end_epoch):
    start_times=[int(ibr['startEpoch']) for ibr in self.ld[self.id]]

    start_times.extend([end_epoch])

    st2=sorted(start_times)

    return [(a-b) for (a,b) in zip(st2[1:],st2[:-1])]
    
    
      
  


