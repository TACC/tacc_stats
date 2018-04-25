import sys
from tacc_stats.analysis.gen import utils

from bokeh.palettes import d3
from bokeh.layouts import gridplot
from bokeh.plotting import figure
import numpy 

class DevPlot():

  def plot(self, job, typename):
    u = utils.utils(job)

    colors = d3["Category20"][20]

    hc = {}
    for i, hostname in enumerate(u.hostnames):
      hc[hostname] = colors[i%20]
    
    plots = []

    schema, _stats  = u.get_type(typename)
    # Plot this type of data
    for index, event in enumerate(schema):
      try:
        p = figure(plot_height = 150, plot_width = 400)
        p.yaxis.axis_label = event
    
        for hostname, stats in _stats.iteritems():               
          rate = stats[:, index]
          rate = numpy.diff(rate)/numpy.diff(job.times)
          p.step(x = u.hours, y = numpy.append(rate, rate[-1]), 
                 mode = "after", line_color = hc[hostname])
        plots += [p]
      except:
        print(event + ' plot failed for jobid ' + job.id )
        print sys.exc_info()
    return gridplot(*plots, ncols = len(plots)/4 + 1)
