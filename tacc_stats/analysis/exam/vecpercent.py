from exams import Test
import numpy
from scipy.stats import tmean

class VecPercent(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'intel_snb'],
      'intel_ivb' : [ 'intel_ivb', 'intel_ivb', 'intel_ivb'],
      'intel_hsw' : [ 'intel_hsw', 'intel_hsw', 'intel_hsw']
      }

  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL'],      
      'intel_ivb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL'],      
      'intel_hsw' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL']
      }

  # If metric is less than threshold then flag 
  comp_operator = '<'
  
  def compute_metric(self):

    gvecrate = 0
    if self.ts.pmc_type == 'amd64' :
      gvecrate += self.arc(self.ts.data[0])

    if self.ts.pmc_type == 'intel_hsw' or self.ts.pmc_type == 'intel_knl' :
      #print "Haswell does not support FLOP counters"
      return
    if self.ts.pmc_type == 'intel_snb':
      schema = self.ts.j.get_schema('intel_snb')
      if 'ERROR' in schema: return
      data = self.ts.j.aggregate_stats('intel_snb')
      nodes = data[1]
      data = data[0].astype(float)
      
      try:
        vectorized = 2*data[:,schema['SSE_DOUBLE_PACKED'].index]+4*data[:,schema['SIMD_DOUBLE_256'].index]
        every = vectorized + data[:,schema['SSE_DOUBLE_SCALAR'].index]
      except: 
        vectorized = 4*data[:,schema['SIMD_D_256'].index]
        every = vectorized + data[:,schema['SSE_D_ALL'].index]

      vecs = numpy.diff(vectorized)/numpy.diff(every)

    self.metric = tmean(vecs)

    return


    
