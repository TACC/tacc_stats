from exams import Test
import numpy

class OSCReqs(Test):
  k1=['osc']
  k2=['reqs']
  comp_operator = '>'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0])
    return  
