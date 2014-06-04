from exams import Test
import numpy, math

class Idle(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','LOAD_L1D_ALL','user'],}
  comp_operator = '>'

  def compute_metric(self):

    mr=[]
    for i in range(len(self.k1)):
      maxrate=numpy.zeros(len(self.ts.t)-1)
      for h in self.ts.j.hosts.keys():
        rate=numpy.divide(numpy.diff(self.ts.data[i][h]),numpy.diff(self.ts.t))
        maxrate=numpy.maximum(rate,maxrate)
      mr.append(maxrate)

    sums=[]
    for i in range(len(self.k1)):
      for h in self.ts.j.hosts.keys():
        rate=numpy.divide(numpy.diff(self.ts.data[i][h]),numpy.diff(self.ts.t))
        sums.append(numpy.sum(numpy.divide(mr[i]-rate,mr[i]))/(len(self.ts.t)-1))

    sums = [0. if math.isnan(x) else x for x in sums]
    self.metric = max(sums)

    return
