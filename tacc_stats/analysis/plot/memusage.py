from plots import Plot
from matplotlib.figure import Figure

class MemUsage(Plot):
  k1=['mem','mem']
  k2=['MemUsed','AnonPages']
  
  def plot(self,jobid,job_data=None):

    self.setup(jobid,job_data=job_data)
    self.fig=Figure(figsize=(8,8),dpi=80)
    self.ax=self.fig.add_subplot(1,1,1)
    self.ax = [self.ax]

    for k in self.ts.j.hosts.keys():
      m=self.ts.data[0][k][0]-self.ts.data[1][k][0]
      m-=self.ts.data[0][k][0][0]
      self.ax[0].plot(self.ts.t/3600.,m)

    self.ax[0].set_ylabel('MemUsed - AnonPages ' +
                  self.ts.j.get_schema(self.ts.k1[0])[self.ts.k2[0]].unit)
    self.ax[0].set_xlabel('Time (hr)')

    self.output('memusage')
