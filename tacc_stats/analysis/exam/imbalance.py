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

    tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
    rng=range(1,len(tmid)) # Throw out first and last
    self.tmid=tmid[rng]         
    
    maxval=numpy.zeros(len(rng))
    minval=numpy.ones(len(rng))*1e100

    self.rate=[]
    for v in self.ts:
      self.rate.append(numpy.divide(numpy.diff(v)[rng],
                                    numpy.diff(self.ts.t)[rng]))
      maxval=numpy.maximum(maxval,self.rate[-1])
      minval=numpy.minimum(minval,self.rate[-1])

    vals=[]
    mean=[]
    std=[]
    for j in range(len(rng)):
      vals.append([])
      for v in self.rate:
        vals[j].append(v[j])
      mean.append(tmean(vals[j]))
      std.append(tstd(vals[j]))

    imbl=maxval-minval

    self.ratio=numpy.divide(std,mean)
    self.ratio2=numpy.divide(imbl,maxval)

    # mean of ratios is the threshold statistic
    self.metric = abs(tmean(self.ratio))
