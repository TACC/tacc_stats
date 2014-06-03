from plots import Plot
import numpy
from tacc_stats.analysis.gen import tspl_utils

class RatioPlot(Plot):

  def __init__(self,imbalance,processes=1):
    self.imbalance=imbalance
    super(RatioPlot,self).__init__(processes=processes)

  def plot(self,jobid,job_data=None):
    if not self.imbalance: 
      print("Generate ratio data using Imbalance test first for job",jobid)
      return

    imb = self.imbalance
  
    # Compute y-axis min and max, expand the limits by 10%
    ymin=min(numpy.minimum(imb.ratio,imb.ratio2))
    ymax=max(numpy.maximum(imb.ratio,imb.ratio2))
    ymin,ymax=tspl_utils.expand_range(ymin,ymax,0.1)

    self.ax=self.fig.subplots(2,1,figsize=(8,8),dpi=80)

    self.ax[0].plot(imb.tmid/3600,imb.ratio)
    self.ax[0].hold=True
    self.ax[0].plot(imb.tmid/3600,imb.ratio2)
    self.ax[0].legend(('Std Dev','Max Diff'), loc=4)
    self.ax[1].hold=True

    ymin1=0. # This is wrong in general, but we don't want the min to be > 0.
    ymax1=0.

    for v in imb.rate:
      ymin1=min(ymin1,min(v))
      ymax1=max(ymax1,max(v))
      self.ax[1].plot(imb.tmid/3600,v)

    ymin1,ymax1=tspl_utils.expand_range(ymin1,ymax1,0.1)
    
    title=imb.ts.title
    if imb.lariat_data.exc != 'unknown':
      title += ', E: ' + imb.lariat_data.exc.split('/')[-1]
    title += ', V: %(V)-8.3g' % {'V' : imb.var}
    self.fig.suptitle(title)
    ax[0].set_xlabel('Time (hr)')
    ax[0].set_ylabel('Imbalance Ratios')
    ax[1].set_xlabel('Time (hr)')
    ax[1].set_ylabel('Total ' + imb.ts.label(imb.ts.k1[0],imb.ts.k2[0]) 
                     + '/s')
    ax[0].set_ylim(bottom=ymin,top=ymax)
    ax[1].set_ylim(bottom=ymin1,top=ymax1)

    if imb.aggregate: full=''
    else: full='_full'

    self.output('ratio_'+full)
