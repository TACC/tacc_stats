from exams import Test

class Load_L2Hits(Test):
  k1 = { 'intel_snb' : ['intel_snb'],
         'intel_ivb' : ['intel_ivb'],
         'intel_hsw' : ['intel_hsw'],      
         'intel_knl' : ['intel_knl']      
        }
  k2 = {'intel_snb' : ['LOAD_OPS_L2_HIT'],
        'intel_ivb' : ['LOAD_OPS_L2_HIT'],
        'intel_hsw' : ['LOAD_OPS_L2_HIT'],
        'intel_knl' : ['MEM_UOPS_RETIRED_L2_HIT_LOADS']
        }

  comp_operator = '>'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0])
