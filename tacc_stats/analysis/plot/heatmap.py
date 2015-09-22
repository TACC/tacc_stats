from plots import Plot
from matplotlib import cm,colors
from matplotlib.figure import Figure
from scipy.stats import tmean, tvar
from numpy import *
class HeatMap(Plot):

  def __init__(self,k1=['intel_snb','intel_snb'],
               k2=['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED'],
               processes=1,aggregate=False,**kwargs):

    self.k1 = k1
    self.k2 = k2
    super(HeatMap,self).__init__(processes=processes,
                                 aggregate=aggregate,
                                 **kwargs)

  def plot(self,jobid,job_data=None):    
    if not self.setup(jobid,job_data=job_data):
      return
    
    ts=self.ts

    host_cpi = {}
    host_names = sorted(ts.data[0].keys())
    for v in host_names:
        ncores = len(ts.data[0][v])
        num = 0
        den = 0
        for k in range(ncores):
          ratio = nan_to_num(diff(ts.data[0][v][k]) / diff(ts.data[1][v][k]))

          try: cpi = vstack((cpi,ratio))
          except: cpi = array([ratio]) 
        
          num += diff(ts.data[0][v][k])
          den += diff(ts.data[1][v][k])

        host_cpi[v] = tmean(nan_to_num(num/den))

    mean_cpi = tmean(host_cpi.values())
    if len(host_cpi.values()) > 1:
      var_cpi  = tvar(host_cpi.values())
    else: var_cpi= 0.0

    self.fig = Figure(figsize=(10,12),dpi=110)
    self.ax=self.fig.add_subplot(1,1,1)

    ycore = arange(cpi.shape[0]+1)
    time = ts.t/3600.
    yhost=arange(len(host_cpi.keys())+1)*ncores + ncores

    fontsize = 8
    set_printoptions(precision=4)
    if len(yhost) > 80:
        fontsize /= 0.5*log(len(yhost))
    self.ax.set_ylim(bottom=ycore.min(),top=ycore.max())
    self.ax.set_yticks(yhost[0:-1]-ncores/2.)

    self.ax.set_yticklabels([key +'(' + "{0:.2f}".format(host_cpi[key]) +')' for key in host_names],fontsize=fontsize)

    self.ax.set_xlim(left=time.min(),right=time.max())
    
    pcm = self.ax.pcolor(time, ycore, cpi,vmin=0.0,vmax=5.0)
    pcm.cmap = cm.get_cmap('jet_r')

    try: self.ax.set_title(self.k2[ts.pmc_type][0] +'/'+self.k2[ts.pmc_type][1] + '\n'+ r'$\bar{Mean}=$'+'{0:.2f}'.format(mean_cpi)+r'$\pm$'+'{0:.2f}'.format(sqrt(var_cpi)))
    except: self.ax.set_title(self.k2[0] +'/'+self.k2[1] + '\n'+ r'$\bar{Mean}$='+'{0:.2f}'.format(mean_cpi)+r'$\pm$'+'{0:.2f}'.format(sqrt(var_cpi)))

    self.fig.colorbar(pcm)
    self.ax.set_xlabel('Time (hrs)')
    self.output('heatmap')
