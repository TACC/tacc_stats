from exams import Test
import numpy
from scipy.stats import tmean

class LowFLOPS(Test):
  k1={'amd64' : ['amd64_core','amd64_sock','cpu'],
      'intel_snb' : [ 'intel_snb', 'intel_snb', 'intel_snb'],
      'intel_ivb' : [ 'intel_ivb', 'intel_ivb', 'intel_ivb'],
      'intel_hsw' : [ 'intel_hsw', 'intel_hsw', 'intel_hsw'],
      'intel_knl' : [ 'intel_knl']
      }
  k2={'amd64' : ['SSE_FLOPS', 'DRAM',      'user'],
      'intel_snb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL'],
      'intel_ivb' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL'],
      'intel_hsw' : ['SIMD_D_256','SSE_D_ALL','LOAD_L1D_ALL'],
      'intel_knl' : ['']
      }

  # If metric is less than threshold then flag 
  comp_operator = '<'
  
  def compute_metric(self):

    gfloprate = 0
    if self.ts.pmc_type == 'amd64' :
      gfloprate += self.arc(self.ts.data[0])
      
    if self.ts.pmc_type == 'intel_hsw' or self.ts.pmc_type == 'intel_knl':
      # print "Haswell chips do not have FLOP counters"
      return

    if self.ts.pmc_type == 'intel_snb':
      schema = self.ts.j.get_schema('intel_snb')
      if 'ERROR' in schema: return
      data = self.ts.j.aggregate_stats('intel_snb')

      try:
        flops = numpy.diff(data[0][:,schema['SSE_DOUBLE_SCALAR'].index] + 2*data[0][:,schema['SSE_DOUBLE_PACKED'].index] + 
                           4*data[0][:,schema['SIMD_DOUBLE_256'].index])/numpy.diff(self.ts.t)
      except: 
        flops = numpy.diff(data[0][:,schema['SSE_D_ALL'].index] + 4*data[0][:,schema['SIMD_D_256'].index])/numpy.diff(self.ts.t)

      flops = flops/data[1]

    self.metric = tmean(flops)/1.0e9

    return


    
