from exams import Test
import numpy
from tacc_stats.analysis.gen import tspl_utils

class Catastrophe(Test):

  # Hash value must be a list
  k1={'amd64' : ['amd64_sock'],
      'intel_snb': ['intel_snb']}
  k2={'amd64' : ['DRAM'],
      'intel_snb': ['LOAD_L1D_ALL']}
  comp_operator = '<'

  def compute_fit_params(self,ind):
    fit=[]
    for v in self.ts:
      rate=numpy.divide(numpy.diff(v),numpy.diff(self.ts.t))
      tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
      r1=range(ind)
      r2=[x + ind for x in range(len(rate)-ind)]
      a=numpy.trapz(rate[r1],tmid[r1])/(tmid[ind]-tmid[0])
      b=numpy.trapz(rate[r2],tmid[r2])/(tmid[-1]-tmid[ind])
      fit.append((a,b))      
    return fit   

  def compute_metric(self):

    bad_hosts=tspl_utils.lost_data(self.ts)
    if len(bad_hosts) > 0:
      print(self.ts.j.id, ': Detected hosts with bad data: ', bad_hosts)
      return

    vals=[]
    for i in [x + 2 for x in range(self.ts.size-4)]:
      vals.append(self.compute_fit_params(i))

    vals2=[]
    for v in vals:
      vals2.append([ b/a for (a,b) in v])


    arr=numpy.array(vals2)
    brr=numpy.transpose(arr)

    (m,n)=numpy.shape(brr)

    r=[]
    for i in range(m):
      jnd=numpy.argmin(brr[i,:])
      r.append((jnd,brr[i,jnd]))

    for (ind,ratio) in r:
      self.metric = min(ratio,self.metric)
    return
