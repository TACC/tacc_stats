from exams import Test
import numpy
from scipy.stats import tmean

class HighCPI(Test):
  k1 = ['intel_snb', 'intel_snb']      
  k2 = ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED' ]

  def test(self,jobid,job_data=None):
    if not self.setup(jobid,job_data=job_data): return
    ts = self.ts

    if "FAIL" in ts.status: return
    if "CANCELLED" in ts.status: return  

    tmid=(ts.t[:-1]+ts.t[1:])/2.0       
    clock_rate = numpy.zeros_like(tmid)
    instr_rate = numpy.zeros_like(tmid)
    for k in ts.j.hosts.keys():
      clock_rate += numpy.diff(ts.data[0][k][0])
      instr_rate += numpy.diff(ts.data[1][k][0])
      
    cpi = tmean(numpy.nan_to_num(clock_rate/instr_rate))

    self.comp2thresh(jobid,cpi)
