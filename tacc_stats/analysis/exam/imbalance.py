from exams import Test
import numpy, operator
from scipy.stats import tmean,tstd

class Imbalance(Test):
  k1=None
  k2=None
  def __init__(self,k1=['intel_snb'],k2=['LOAD_L1D_ALL'],processes=1,aggregate=False,**kwargs):
    self.k1=k1
    self.k2=k2

    if aggregate:
      kwargs['min_hosts'] = 2
    kwargs['aggregate'] = aggregate
    kwargs['waynesses']=16
    super(Imbalance,self).__init__(processes=processes,**kwargs)

  def test(self,jobid,job_data=None):
    
    if not self.setup(jobid,job_data=job_data): return

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
    var=tmean(self.ratio) 
    self.ratios[self.ts.j.id]=[var,self.ts.owner]
    self.comp2thresh(jobid,abs(var))

  def find_top_users(self):
    users={}

    for k in self.ratios.keys():
      u=self.ratios[k][1]
      if not u in users:
        users[u]=[]
        users[u].append(0.)
        users[u].append([])
      else:
        users[u][0]=max(users[u][0],self.ratios[k][0])
        users[u][1].append(k)


    a=[ x[0] for x in sorted(users.iteritems(),
                             key=operator.itemgetter(1), reverse=True) ]
    maxi=len(a)+1
    maxi=min(10,maxi)
    print('---------top 10----------')
    for u in a[0:maxi]:
      print(u + ' ' + str(users[u][0]) + ' ' + ' '.join(users[u][1]))
    return users
