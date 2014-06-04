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
    clock_rate = numpy.zeros_like(tmid)
    instr_rate = numpy.zeros_like(tmid)
    for k in ts.j.hosts.keys():
      clock_rate += numpy.diff(ts.data[0][k][0])
      instr_rate += numpy.diff(ts.data[1][k][0])
      
    self.metric = tmean(numpy.nan_to_num(clock_rate/instr_rate))
