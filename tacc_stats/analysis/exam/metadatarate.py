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

  def test(self,jobid,job_data=None):
    if not self.setup(jobid,job_data=job_data): return
    ts = self.ts

    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    meta_rate = numpy.zeros_like(tmid)

    for k in ts.j.hosts.keys():
      meta_rate+=numpy.diff(ts.assemble(range(0,len(self.k1)),k,0))/numpy.diff(ts.t)

    meta_rate  /= float(ts.numhosts)
    
    self.comp2thresh(jobid,numpy.max(meta_rate))

    return  
