from exams import Test
import numpy
from scipy.stats import tmean

class MemBw(Test):

  k1=['intel_snb_imc', 'intel_snb_imc']
  k2=['CAS_READS', 'CAS_WRITES']
  comp_operator = '>'

  def compute_metric(self):

    peak = 76.*1.e9
    gdramrate = numpy.zeros(len(self.ts.t)-1)
    for h in self.ts.j.hosts.keys():
      gdramrate += numpy.divide(numpy.diff(64.*self.ts.assemble([0,1],h,0)),
                                numpy.diff(self.ts.t))

    mdr=tmean(gdramrate)/self.ts.numhosts
    self.metric = mdr/peak

    return
