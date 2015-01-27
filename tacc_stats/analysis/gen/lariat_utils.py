from __future__ import print_function
import json
import datetime, time, os, fnmatch
import re
import textwrap

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
    print(self.value)

class LariatData:

  equiv_patterns = {
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

  def __init__(self,directory=None,daysback=3):
    # Initialize to invalid/empty states
    self.ld_json=dict()
    self.loaded_files = []
    self.directory = directory
    self.daysback = daysback

  # Can accept ts object or jobid and end_epoch
  def set_job(self,job,end_time=None):

    try:
      jobid = job.j.id
      end_time = job.j.end_time
    except: 
      jobid = job

    # Find the set of JSON files matching the end_time date or epoch
    # Initialize to invalid/empty states
    self.id=0
    self.user='nobody'
    self.exc='unknown'
    self.cwd='unknown'
    self.threads=1
    self.cores=None
    self.nodes=None
    self.wayness=None

    # Find the json file the job should be in
    if self.directory == None: 
      print("Please initialize LariatData with a valid lariat directory")

    # Check if job is in json.
    # Load if it is not unless file has been loaded already.
    if jobid not in self.ld_json:
      self.load_file(jobid,end_time)
            
    # If job data exists it should be here.
    try:
      entry = self.ld_json[jobid][0]
    except KeyError:
      print("Lariat Data for",jobid,"absent.")
      self.ld_json[jobid] = [None]
    if not self.ld_json[jobid][0]: return
    
    self.id=entry['jobID']
    self.user=entry['user']
    self.exc=replace_and_shorten_path_bits(entry['exec'],self.user,60)
    self.cwd=replace_and_shorten_path_bits(entry['cwd'],self.user,60)
    self.threads=int(entry['numThreads'])
    self.cores=int(entry['numCores'])
    self.nodes=int(entry['numNodes'])
    self.wayness=int(float(self.cores)/self.nodes)

  def load_file(self,jobid,end_time):
    for day in range(self.daysback+1):

      delta = datetime.timedelta(days=day)
      try:
        date_obj = datetime.datetime.fromtimestamp(end_time)
      except:      
        date_obj = datetime.datetime.strptime(end_time,"%Y-%m-%d")
      date = (date_obj-delta).strftime("%Y-%m-%d")

      for root, dirnames, filenames in os.walk(self.directory):
        for filename in fnmatch.filter(filenames,'*'+date+'.json'):

          if filename in self.loaded_files: continue
          else: self.loaded_files.append(filename)

          try:
            with open(os.path.join(root,filename)) as fd:
              self.ld_json.update(json.loads(re.sub(r'\\','',fd.read())))
              print('Loaded Lariat Data from',filename)
          except IOError:
            print("Load failed for",filename)
          if jobid in self.ld_json: return

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

  def get_runtimes(self,end_time):
    start_times=[int(ibr['startEpoch']) for ibr in self.ld_json[self.id]]
    start_times.extend([end_time])
    st2=sorted(start_times)
    return [(a-b) for (a,b) in zip(st2[1:],st2[:-1])]
    
    
      
  


