from exams import Test

class Load_L2Hits(Test):
  k1 = ['intel_snb']      
  k2 = ['LOAD_OPS_L2_HIT']
  comp_operator = '>'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0])
