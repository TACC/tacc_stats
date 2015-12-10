from exams import Test
import numpy

class MDCWait(Test):
  k1=['mdc', 'mdc']
  k2=['reqs', 'wait']
  comp_operator = '>'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[1])/self.arc(self.ts.data[0])
    return  
