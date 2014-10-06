from exams import Test
import numpy

class HighCPLD(Test):
  k1 = ['intel_snb', 'intel_snb']      
  k2 = ['CLOCKS_UNHALTED_REF','LOAD_L1D_ALL' ]
  comp_operator = '>'

  def compute_metric(self):

    cpld += self.arc(self.ts.data[0])/self.arc(self.ts.data[1])

    self.metric = cpld
