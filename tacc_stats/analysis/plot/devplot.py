from plots import Plot
from matplotlib.figure import Figure
class DevPlot(Plot):

  def __init__(self,k1={'intel_snb' : ['intel_snb','intel_snb','intel_snb']},k2={'intel_snb':['LOAD_1D_ALL','INSTRUCTIONS_RETIRED','LOAD_OPS_ALL']},processes=1,**kwargs):
    self.k1 = k1
    self.k2 = k2
    super(DevPlot,self).__init__(processes=processes,**kwargs)

  def plot(self,jobid,job_data=None):
    self.setup(jobid,job_data=job_data)
    cpu_name = self.ts.pmc_type
    type_name=self.k1[cpu_name][0]
    events = self.k2[cpu_name]

    ts=self.ts

    n_events = len(events)
    self.fig = Figure(figsize=(8,n_events*2+3),dpi=110)

    do_rate = True
    scale = 1.0
    if type_name == 'mem': 
      do_rate = False
      scale=2.0**10
    if type_name == 'cpu':
      scale=ts.wayness*100.0

    for i in range(n_events):
      self.ax = self.fig.add_subplot(n_events,1,i+1)
      self.plot_lines(self.ax, [i], xscale=3600., yscale=scale, do_rate = do_rate)
      self.ax.set_ylabel(events[i],size='small')
    self.ax.set_xlabel("Time (hr)")
    self.fig.subplots_adjust(hspace=0.5)
    self.fig.tight_layout()

    self.output('devices')
