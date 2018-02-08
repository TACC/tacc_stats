from exams import Test

class MemBw(Test):

  k1={'intel_snb' : ['intel_snb_imc', 'intel_snb_imc'],
      'intel_ivb' : ['intel_ivb_imc', 'intel_ivb_imc'],
      'intel_hsw' : ['intel_hsw_imc', 'intel_hsw_imc'],
      'intel_bdw' : ['intel_bdw_imc', 'intel_bdw_imc'],
      'intel_knl' : ['intel_knl_mc_dclk', 'intel_knl_mc_dclk'],
      'intel_skx' : ['intel_skx_imc', 'intel_skx_imc'],
      }

  k2={'intel_snb' : ['CAS_READS', 'CAS_WRITES'],
      'intel_ivb' : ['CAS_READS', 'CAS_WRITES'],
      'intel_hsw' : ['CAS_READS', 'CAS_WRITES'],
      'intel_knl' : ['CAS_READS', 'CAS_WRITES'],
      'intel_skx' : ['CAS_READS', 'CAS_WRITES']
      }

  peak = {'intel_snb' : 76.*1.e9,
          'intel_ivb' : 76.*1.e9,
          'intel_hsw' : 104.*1.e9,
          'intel_knl' : 90.*1.e9,
          'intel_skx' : 202.*1.e9
          }

  def compute_metric(self):

    gdramrate = 64*(self.arc(self.ts.data[0])+self.arc(self.ts.data[1]))
    self.metric = gdramrate*(self.peak[self.ts.pmc_type])**-1
    return
