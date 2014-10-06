from exams import Test

class MemBw(Test):

  k1=['intel_snb_imc', 'intel_snb_imc']
  k2=['CAS_READS', 'CAS_WRITES']
  peak = 76.*1.e9 # SNB value from stream
  comp_operator = '>'

  def compute_metric(self):

    gdramrate = 64*(self.arc(self.ts.data[0])+self.arc(self.ts.data[1]))
    
    self.metric = gdramrate*(self.peak)**-1

    return
