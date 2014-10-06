# This will compute the maximum memory usage recorded
# by monitor.  It only samples at x mn intervals and
# may miss high water marks in between.
from exams import Test
from numpy import amax

class MemUsage(Test):

  k1=['mem', 'mem', 'mem']
  k2=['MemUsed', 'FilePages', 'Slab']
  
  comp_operator = '<'
  
  def compute_metric(self):
    # mem usage in GB
    max_memusage = 0 
    for h in self.ts.j.hosts.keys():
      max_memusage = max(max_memusage,amax(self.ts.data[0][h][0]-self.ts.data[1][h][0]-self.ts.data[2][h][0]))

    self.metric = max_memusage/(2.**30)

    return
