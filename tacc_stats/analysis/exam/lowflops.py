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

  # If Metric is less than Threshold than flag 
  comp_operator = '<'
  
  def compute_metric(self):

    ts=self.ts
    gfloprate = numpy.zeros(len(ts.t)-1)
    gdramrate = numpy.zeros(len(ts.t)-1)
    gcpurate  = numpy.zeros(len(ts.t)-1)
    for h in ts.j.hosts.keys():
      if ts.pmc_type == 'amd64' :
        gfloprate += numpy.divide(numpy.diff(ts.data[0][h][0]),numpy.diff(ts.t))
        gdramrate += numpy.divide(numpy.diff(ts.data[1][h][0]),numpy.diff(ts.t))
        gcpurate  += numpy.divide(numpy.diff(ts.data[2][h][0]),numpy.diff(ts.t))
      elif ts.pmc_type == 'intel_snb':
        gfloprate += numpy.divide(numpy.diff(ts.data[0][h][0]),numpy.diff(ts.t))
        gfloprate += numpy.divide(numpy.diff(ts.data[1][h][0]),numpy.diff(ts.t))
        gdramrate += numpy.divide(numpy.diff(ts.data[2][h][0]),numpy.diff(ts.t))
        gcpurate  += numpy.divide(numpy.diff(ts.data[3][h][0]),numpy.diff(ts.t))
        
    mfr=tmean(gfloprate)/ts.numhosts
    mdr=tmean(gdramrate)/ts.numhosts
    mcr=tmean(gcpurate)/(ts.numhosts*ts.wayness*100.)



    if (mcr/self.peak[ts.pmc_type][2] > 0.5):
      self.metric = (mfr/self.peak[ts.pmc_type][0])/(mdr/self.peak[ts.pmc_type][1]) 
    else: 
      self.metric = 0

    return


    
