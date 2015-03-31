# This will compute the maximum memory usage recorded
# by monitor.  It only samples at x mn intervals and
# may miss high water marks in between.
from exams import Test
from numpy import amax, diff, zeros_like

class LustreLoad(Test):

  k1=['llite']
  k2=['open']
  
  comp_operator = '>'
  
  def compute_metric(self):
    # Lustre Load
    I_dt = 1.0/diff(self.ts.t)
    load = zeros_like(I_dt)
    for h in self.ts.j.hosts.keys():
      load += diff(self.ts.data[0][h][0])*I_dt
    self.metric = max(load)

    return
