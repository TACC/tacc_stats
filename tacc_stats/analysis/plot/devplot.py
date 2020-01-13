import sys
from tacc_stats.analysis.gen import utils

from bokeh.palettes import d3
from bokeh.layouts import gridplot
from bokeh.models import HoverTool, ColumnDataSource, Plot, Grid, DataRange1d, LinearAxis
from bokeh.models.glyphs import Step
import numpy 

class DevPlot():

  def add_axes(self, plot, label):
    xaxis = LinearAxis()
    yaxis = LinearAxis()      
    yaxis.axis_label = label
    plot.add_layout(xaxis, 'below')        
    plot.add_layout(yaxis, 'left')
    plot.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
    plot.add_layout(Grid(dimension=1, ticker=yaxis.ticker))
    return plot

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
        plot = Plot(plot_width=400, plot_height=150, 
                    x_range = DataRange1d(), y_range = DataRange1d())                  
        for hostname, stats in _stats.items():               
          rate = stats[:, index]
          if typename == "mem" or typename == "proc":
            source = ColumnDataSource({"x" : u.hours, "y" : rate})
            plot.add_glyph(source, Step(x = "x", y = "y", mode = "after", 
                                        line_color = hc[hostname]))
          else: 
            rate = numpy.diff(rate)/numpy.diff(job.times)
            source = ColumnDataSource({"x" : u.hours, "y" : numpy.append(rate, rate[-1])})
            plot.add_glyph(source, Step(x = "x", y = "y", mode = "after", 
                                        line_color = hc[hostname]))
        if "FP_ARITH_INST_RETIRED" in event: event = event.split("FP_ARITH_INST_RETIRED_")[1]
        plots += [self.add_axes(plot, event)]
      except:
        print(event + ' plot failed for jobid ' + job.id )
        print(sys.exc_info())
    return gridplot(plots, ncols = len(plots)//4 + 1)
