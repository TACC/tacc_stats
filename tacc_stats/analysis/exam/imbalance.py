from exams import Test
import numpy, operator
from scipy.stats import tmean,tstd

class Imbalance(Test):
  k1 = None
  k2 = None
  comp_operator = '>'
  
  def __init__(self,k1=['intel_snb'],k2=['LOAD_L1D_ALL'],processes=1,aggregate=False,**kwargs):
    self.k1=k1
    self.k2=k2

    if aggregate:
      kwargs['min_hosts'] = 2
    kwargs['aggregate'] = aggregate
    kwargs['waynesses']=16
    super(Imbalance,self).__init__(processes=processes,**kwargs)

  def compute_metric(self):

    rate = self.arc(self.ts.data[0])
    mean = tmean(self.val.values())
    std  = tstd(self.val.values())
    self.metric = abs(std/mean)
