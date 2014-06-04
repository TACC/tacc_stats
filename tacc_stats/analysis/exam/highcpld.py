from exams import Test
import numpy

class HighCPLD(Test):
  k1 = ['intel_snb', 'intel_snb']      
  k2 = ['CLOCKS_UNHALTED_REF','LOAD_L1D_ALL' ]
  comp_operator = '>'

  def compute_metric(self):
    ts = self.ts

    tmid=(ts.t[:-1]+ts.t[1:])/2.0       
    clock_rate = numpy.zeros_like(tmid)
    instr_rate = numpy.zeros_like(tmid)
    for k in ts.j.hosts.keys():
      clock_rate += numpy.diff(ts.assemble([0],k,0))/numpy.diff(ts.t)
      instr_rate += numpy.diff(ts.assemble([1],k,0))/numpy.diff(ts.t)

    self.metric = tmean(clock_rate/instr_rate)

    return
