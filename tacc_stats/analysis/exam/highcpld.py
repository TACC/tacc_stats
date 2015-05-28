from exams import Test
import numpy

class HighCPLD(Test):

  k1 = {'intel_snb' : ['intel_snb', 'intel_snb'],
        'intel_hsw' : ['intel_hsw', 'intel_hsw']
        }      
  k2 = {'intel_snb' : ['CLOCKS_UNHALTED_REF','LOAD_1D_ALL'],
        'intel_hsw' : ['CLOCKS_UNHALTED_REF','LOAD_1D_ALL']
        }

  comp_operator = '>'

  def compute_metric(self):

    cpld = self.arc(self.ts.data[0])/self.arc(self.ts.data[1])

    self.metric = cpld
