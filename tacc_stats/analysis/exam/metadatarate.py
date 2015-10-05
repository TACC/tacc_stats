from exams import Test
import numpy

class MetaDataRate(Test):
  k1=['llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', ]
  k2=['open','close','mmap','fsync','setattr',
      'truncate','flock','getattr','statfs','alloc_inode',
      'setxattr',' listxattr',
      'removexattr', 'readdir',
      'create','lookup','link','unlink','symlink','mkdir',
      'rmdir','mknod','rename',]
  comp_operator = '>'

  def compute_metric(self):

    ts = self.ts
    tmid=(ts.t[:-1]+ts.t[1:])/2.0
    meta_rate = numpy.zeros_like(tmid)
 
    for k in ts.j.hosts.keys():
      meta_rate+=numpy.diff(ts.assemble(range(0,len(ts.k1)),k,0))/numpy.diff(ts.t)
    
    self.metric = numpy.max(meta_rate)
    return  
