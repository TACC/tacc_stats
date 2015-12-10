from exams import Test
import numpy

class LLiteOpenClose(Test):
  k1=['llite', 'llite']
  k2=['open','close']

  comp_operator = '>'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0]) + self.arc(self.ts.data[1])
    return  
