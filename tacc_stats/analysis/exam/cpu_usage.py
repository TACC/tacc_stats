from exams import Test

class CPU_Usage(Test):
  k1={'amd64' : ['cpu'],
      'intel_snb' : ['cpu'],}
  k2={'amd64' : ['user'],
      'intel_snb' : ['user'],}
  comp_operator = '<'

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0])
    return
