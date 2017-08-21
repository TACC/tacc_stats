from exams import Test

class CPU_Usage(Test):
  k1 = ['cpu']
  k2 = ['user']

  def compute_metric(self):
    self.metric = self.arc(self.ts.data[0])
    return
