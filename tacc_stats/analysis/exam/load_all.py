from exams import Test

class Load_All(Test):
  k1 = { 'intel_snb' : ['intel_snb'],
         'intel_hsw' : ['intel_hsw']      
        }
  k2 = {'intel_snb' : ['LOAD_OPS_ALL'],
        'intel_hsw' : ['LOAD_OPS_ALL']
        }

  comp_operator = '>'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0])
