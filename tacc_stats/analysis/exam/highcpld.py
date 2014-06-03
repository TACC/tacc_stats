from exams import Test

class HighCPLD(Test):
  k1 = ['intel_snb', 'intel_snb']      
  k2 = ['CLOCKS_UNHALTED_REF','LOAD_L1D_ALL' ]

  def test(self,jobid,job_data=None):
    if not self.setup(jobid,job_data=job_data): return
    ts = self.ts

    if "FAIL" in ts.status: return
    if "CANCELLED" in ts.status: return  

    tmid=(ts.t[:-1]+ts.t[1:])/2.0       
    clock_rate = numpy.zeros_like(tmid)
    instr_rate = numpy.zeros_like(tmid)
    for k in ts.j.hosts.keys():
      clock_rate += numpy.diff(ts.assemble([0],k,0))/numpy.diff(ts.t)
      instr_rate += numpy.diff(ts.assemble([1],k,0))/numpy.diff(ts.t)

    cpi = tmean(clock_rate/instr_rate)

    self.comp2thresh(jobid,cpi)
