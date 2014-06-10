from exams import Test
import numpy
from scipy.stats import tmean

class HighCPI(Test):
  k1 = ['intel_snb', 'intel_snb']      
  k2 = ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED' ]
  comp_operator = '>'

  def compute_metric(self):

    ts = self.ts

    tmid=(ts.t[:-1]+ts.t[1:])/2.0       

    # Average over each node's time series turning nan's to zero's
    ratio = {}
    for k in ts.j.hosts.keys():
      ratio[k] = tmean(numpy.nan_to_num(numpy.diff(ts.data[0][k][0])/numpy.diff(ts.data[1][k][0])))

    # Average of time-averaged nodes
    self.metric = tmean(ratio.values())
