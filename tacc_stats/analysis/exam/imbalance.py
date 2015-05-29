from exams import Test
import numpy, operator
from scipy.stats import tmean,tstd

class Imbalance(Test):
  k1 = None
  k2 = None
  k1 = { 'intel_snb' : ['intel_snb'],
         'intel_hsw' : ['intel_hsw']      
        }
  k2 = {'intel_snb' : ['LOAD_L1D_ALL'],
        'intel_hsw' : ['LOAD_L1D_ALL']
        }


  comp_operator = '>'
  
  def __init__(self,**kwargs):


    kwargs['min_hosts'] = 2
    super(Imbalance,self).__init__(**kwargs)

  def compute_metric(self):

    rate = self.arc(self.ts.data[0])
    mean = tmean(self.val.values())
    std  = tstd(self.val.values())
    self.metric = abs(std/mean)
