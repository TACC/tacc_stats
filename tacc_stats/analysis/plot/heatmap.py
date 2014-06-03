from plots import Plot
from matplotlib.figure import Figure
import numpy

class HeatMap(Plot):

  def __init__(self,k1=['intel_snb','intel_snb'],
               k2=['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
               processes=1,aggregate=False,**kwargs):

    self.k1 = k1
    self.k2 = k2
    super(HeatMap,self).__init__(processes=processes,aggregate=aggregate,**kwargs)

  def plot(self,jobid,job_data=None):
    self.setup(jobid,job_data=job_data)
    ts=self.ts

    hosts = []
    for v in ts.data[0]:
        hosts.append(v)
        ncores = len(ts.data[0][v])
        for k in range(ncores):
          num = numpy.array(numpy.diff(ts.data[0][v][k]),dtype=numpy.float64)
          den = numpy.array(numpy.diff(ts.data[1][v][k]),dtype=numpy.float64)
          ratio = numpy.divide(num,den)
          ratio = numpy.nan_to_num(ratio)
          try: cpi = numpy.vstack((cpi,ratio))
          except: cpi = numpy.array([ratio]) 

    cpi_min, cpi_max = cpi.min(), cpi.max()

    mean_cpi = numpy.mean(cpi)
    var_cpi  = numpy.var(cpi)
    self.fig = Figure(figsize=(8,12),dpi=110)
    self.ax=self.fig.add_subplot(1,1,1)

    ycore = numpy.arange(cpi.shape[0]+1)
    time = ts.t/3600.
    yhost=numpy.arange(len(hosts)+1)*ncores + ncores

    fontsize = 10

    if len(yhost) > 80:
        fontsize /= 0.5*numpy.log(len(yhost))
    self.ax.set_ylim(bottom=ycore.min(),top=ycore.max())
    self.ax.set_yticks(yhost[0:-1]-ncores/2.)
    self.ax.set_yticklabels(hosts)#,va='center')
    self.ax.set_xlim(left=time.min(),right=time.max())

    pcm = self.ax.pcolormesh(time, ycore, cpi)
    numpy.set_printoptions(precision=4)
    try: self.ax.set_title(self.k2[ts.pmc_type][0] +'/'+self.k2[ts.pmc_type][1] + '\n'+ r'$\bar{Mean}=$'+'{0:.2f}'.format(mean_cpi)+' '+r'$Var=$' +  '{0:.2f}'.format(var_cpi))
    except: self.ax.set_title(self.k2[0] +'/'+self.k2[1] + '\n'+ r'$\bar{Mean}$='+'{0:.2f}'.format(mean_cpi)+' '+r'$Var=$' +  '{0:.2f}'.format(var_cpi))
    self.fig.colorbar(pcm)
    self.ax.set_xlabel('Time (hrs)')
    self.output('heatmap')
