from plots import Plot
from matplotlib.figure import Figure
from tacc_stats.analysis.gen import tspl_utils
import numpy 

class MetaDataRatePlot(Plot):
  k1=['llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite',]
  k2=['open','close','mmap','fsync','setattr',
      'truncate','flock','getattr','statfs','alloc_inode',
      'setxattr',' listxattr',
      'removexattr', 'readdir',
      'create','lookup','link','unlink','symlink','mkdir',
      'rmdir','mknod','rename',]

  def plot(self,jobid,job_data=None):
    self.setup(jobid,job_data=job_data)

    ts = self.ts
    self.fig = Figure(figsize=(10,8),dpi=80)
    self.ax=self.fig.add_subplot(1,1,1)
    self.ax=[self.ax]
    self.fig.subplots_adjust(hspace=0.35)

    markers = ('o','x','+','^','s','8','p',
                 'h','*','D','<','>','v','d','.')

    colors  = ('b','g','r','c','m','k','y')
    tmid=(self.ts.t[:-1]+self.ts.t[1:])/2.0
    cnt=0
    for v in ts.data:
      for host in v:
        for vals in v[host]:
          rate=numpy.diff(vals)/numpy.diff(ts.t)
          c=colors[cnt % len(colors)]
          m=markers[cnt % len(markers)]

          self.ax[0].plot(tmid/3600., rate, marker=m,
                  markeredgecolor=c, linestyle='-', color=c,
                  markerfacecolor='None', label=self.k2[cnt])
          self.ax[0].hold=True
      cnt=cnt+1

    self.ax[0].set_ylabel('Meta Data Rate (op/s)')
    tspl_utils.adjust_yaxis_range(self.ax[0],0.1)

    handles,labels=self.ax[0].get_legend_handles_labels()
    new_handles={}
    for h,l in zip(handles,labels):
      new_handles[l]=h

    box = self.ax[0].get_position()
    self.ax[0].set_position([box.x0, box.y0, box.width * 0.9, box.height])
    self.ax[0].legend(new_handles.values(),new_handles.keys(),prop={'size':8},
                      bbox_to_anchor=(1.05,1), borderaxespad=0., loc=2)

    self.output('metadata')
