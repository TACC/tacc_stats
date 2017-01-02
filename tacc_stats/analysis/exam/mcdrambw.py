from exams import Test

class MCDRAMBW(Test):

  k1={'intel_knl' : ['intel_knl_edc_eclk', 'intel_knl_edc_uclk', 'intel_knl_edc_uclk', 'intel_knl_edc_eclk', 'intel_knl_mc_dclk']
      }

  k2={'intel_knl' : ['RPQ_INSERTS', 'EDC_MISS_CLEAN', 'EDC_MISS_DIRTY', 'WPQ_INSERTS', 'CAS_READS']
      }

  comp_operator = '>'

  def compute_metric(self):
    
    if "Flat" in self.ts.j.acct['queue']:
      print self.ts.j.acct['queue']
      gdramrate = 64*(self.arc(self.ts.data[0]) + self.arc(self.ts.data[3]))
    else:
      gdramrate = 64*(self.arc(self.ts.data[0]) - self.arc(self.ts.data[1]) - self.arc(self.ts.data[2]) + self.arc(self.ts.data[3]) - self.arc(self.ts.data[4]) )

    self.metric = gdramrate/(1024.0*1024.0*1024.0)
    return
