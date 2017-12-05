from exams import Test

class HighCPI(Test):
  k1 = {'intel_snb' : ['intel_snb', 'intel_snb'],
        'intel_ivb' : ['intel_ivb', 'intel_ivb'],
        'intel_hsw' : ['intel_hsw', 'intel_hsw'],
        'intel_bdw' : ['intel_bdw', 'intel_bdw'],
        'intel_knl' : ['intel_knl', 'intel_knl'],
        'intel_skx' : ['intel_skx', 'intel_skx'],
        }      
  k2 = {'intel_snb' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
        'intel_ivb' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
        'intel_hsw' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],        
        'intel_bdw' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],        
        'intel_knl' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
        'intel_skx' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED']
        }

  def compute_metric(self):
    
    cpi = self.arc(self.ts.data[0])/self.arc(self.ts.data[1])
    self.metric = cpi
