from exams import Test
import numpy, math

class Idle(Test):
  k1={'amd64' : ['cpu'],
      'intel_snb' : ['cpu'],
      'intel_hsw' : ['cpu']
      }
  k2={'amd64' : ['user'],
      'intel_snb' : ['user'],
      'intel_hsw' : ['user']
      }

  comp_operator = '>'

  def compute_metric(self):

    mr = []

    # Get max at each time-stamp over nodes
    for i in range(len(self.ts.k1)):
      max_fraction = numpy.zeros(len(self.ts.t)-1)
      for h in self.ts.j.hosts.keys():
        max_fraction = numpy.maximum(max_fraction,numpy.diff(self.ts.data[i][h][0])/numpy.diff(self.ts.t))
      mr.append(max_fraction)

    sums = []
    for i in range(len(self.ts.k1)):
      for h in self.ts.j.hosts.keys():
        fraction = numpy.diff(self.ts.data[i][h][0])/numpy.diff(self.ts.t)
        sums.append(numpy.mean((mr[i]-fraction)/mr[i]))

    sums = [0. if math.isnan(x) else x for x in sums]
    self.metric = max(sums)
    
    

    return
