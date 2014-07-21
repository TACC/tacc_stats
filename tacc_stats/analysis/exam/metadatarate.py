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

    meta_rate = 0
    for i in range(0,len(self.ts.k1)):
      meta_rate += self.arc(self.ts.data[i])
    
    self.metric = meta_rate
    return  
