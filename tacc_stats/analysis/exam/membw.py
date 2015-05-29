from exams import Test

class MemBw(Test):

  k1={'intel_snb' : ['intel_snb_imc', 'intel_snb_imc'],
      'intel_hsw' : ['intel_hsw_imc', 'intel_hsw_imc']
      }

  k2={'intel_snb' : ['CAS_READS', 'CAS_WRITES'],
      'intel_hsw' : ['CAS_READS', 'CAS_WRITES']
      }

  peak = {'intel_snb' : 76.*1.e9, # SNB value from stream
          'intel_hsw' : 104.*1.e9
          }
  comp_operator = '>'

  def compute_metric(self):

    gdramrate = 64*(self.arc(self.ts.data[0])+self.arc(self.ts.data[1]))
    self.metric = gdramrate*(self.peak[self.ts.pmc_type])**-1
    return
