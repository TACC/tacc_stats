from exams import Test

class HighCPI(Test):
  k1 = {'intel_snb' : ['intel_snb', 'intel_snb'],
        'intel_ivb' : ['intel_ivb', 'intel_ivb'],
        'intel_hsw' : ['intel_hsw', 'intel_hsw'],
        'intel_knl' : ['intel_knl', 'intel_knl']
        }      
  k2 = {'intel_snb' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
        'intel_ivb' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
        'intel_hsw' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],        
        'intel_knl' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED']
        }
  comp_operator = '>'

  def compute_metric(self):

    cpi = self.arc(self.ts.data[0])/self.arc(self.ts.data[1])
    self.metric = cpi
