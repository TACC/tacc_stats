from exams import Test
import numpy
from tacc_stats.analysis.gen import tspl_utils

class Catastrophe(Test):

  # Hash value must be a list
  k1={'amd64' : ['amd64_sock'],
      'intel_snb' : ['intel_snb'],
      'intel_hsw' : ['intel_hsw']
      }
  k2={'amd64' : ['DRAM'],
      'intel_snb' : ['LOAD_L1D_ALL'],
      'intel_hsw' : ['LOAD_L1D_ALL']
      }
  comp_operator = '<'

  def compute_fit_params(self,ind):
    fit=[]
    r1=range(ind)
    r2=[x + ind for x in range(len(self.dt)-ind)]

    for v in self.ts:
      rate=numpy.divide(numpy.diff(v),self.dt)
      # integral before time slice 
      a=numpy.trapz(rate[r1],self.tmid[r1])/(self.tmid[ind]-self.tmid[0])
      # integral after time slice
      b=numpy.trapz(rate[r2],self.tmid[r2])/(self.tmid[-1]-self.tmid[ind])
      # ratio of integral after time over before time
      fit.append(b/a)      
    return fit   

  def compute_metric(self):

    if len(tspl_utils.lost_data(self.ts)) > 0: 
      print(self.ts.j.id, ': Detected hosts with bad data')
      return

    self.tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
    self.dt = numpy.diff(self.ts.t)

    #skip first and last two time slices
    vals=[]
    for i in [x + 2 for x in range(self.ts.size-4)]:
      vals.append(self.compute_fit_params(i))

    #times  hosts ---->
    #  |
    #  |
    #  |
    #  V
    try:
      self.metric = numpy.array(vals).min()
    except: pass
    return
