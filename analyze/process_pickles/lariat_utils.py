import json
import time, os, fnmatch

def make_date_string(t):
  lt=time.localtime(t)
  return '%(y)04d-%(m)02d-%(d)02d' % { 'y' : lt.tm_year, 'm' : lt.tm_mon,
                                       'd' : lt.tm_mday }

class LariatDataException(Exception):
  def __init__(self,arg):
    self.value=arg
    print self.value

class LariatData:
  def __init__(self,jobid,end_epoch,directory):
    ds=make_date_string(end_epoch)
    matches=[]
    for root, dirnames, filenames in os.walk(directory):
      for fn in fnmatch.filter(filenames,'*'+ds+'.json'):
        matches.append(os.path.join(root,fn))

    self.jobid=jobid

    if len(matches) == 0:
      self.ld=None
      self.user='nobody'
      self.exc='unknown'
      self.cwd='unknown'
      print 'File for ' + jobid + ' not found in ' + directory
    else:
      self.ld=json.load(open(matches[0]))
      try:
        self.user=self.ld[jobid][0]['user']
        self.exc=self.ld[jobid][0]['exec']
        self.cwd=self.ld[jobid][0]['cwd']
      except KeyError:
        print str(jobid) + ' did not call ibrun' + \
              ' or has no lariat data for some other reason'
        self.user='nobody'
        self.exc='unknown'
        self.cwd='unknown'

  def title(self):
    title='E: ' + self.exc
    if (self.cwd != 'unknown'):
      if ((len(self.exc) + len (self.cwd)) > 50):
        sep=',\n'
      else:
        sep=', '
      title += sep + 'CWD: ' + self.cwd
    return title
  
      

