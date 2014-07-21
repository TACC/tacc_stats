from exams import Test
import numpy
from scipy.stats import tmean

class LowFLOPS(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'intel_snb', 'cpu'],}
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL','user'],}

  peak={'amd64' : [2.3e9*16*2, 24e9, 1.],
        'intel_snb' : [ 16*2.7e9*2, 16*2.7e9/2.*64., 1.],}

  # If metric is less than threshold then flag 
  comp_operator = '<'
  
  def compute_metric(self):

    gfloprate = 0
    gdramrate = 0
    gcpurate  = 0

    if self.ts.pmc_type == 'amd64' :
      gfloprate += self.arc(self.ts.data[0])
      gdramrate += self.arc(self.ts.data[1])
      gcpurate  += self.arc(self.ts.data[2])
        
    elif self.ts.pmc_type == 'intel_snb':
      gfloprate += self.arc(self.ts.data[0])+self.arc(self.ts.data[1])
      gdramrate += self.arc(self.ts.data[2])
      gcpurate  += self.arc(self.ts.data[3])

    # Percent of peak
    pfr=gfloprate/self.peak[self.ts.pmc_type][0]
    pdr=gdramrate/self.peak[self.ts.pmc_type][1]
    pcr=gcpurate/(self.ts.wayness*100.)

    if (pcr > 0.5):
      self.metric = pfr/pdr 
    else: 
      self.metric = 0

    return


    
