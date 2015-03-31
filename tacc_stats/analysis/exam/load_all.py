from exams import Test

class Load_All(Test):
  k1 = ['intel_snb']      
  k2 = ['LOAD_OPS_ALL']
  comp_operator = '>'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0])
