import sys
from tacc_stats.analysis.gen import utils

from bokeh.palettes import d3
from bokeh.layouts import gridplot
from bokeh.plotting import figure
from bokeh.models import HoverTool
import numpy 

class MasterPlot():

  def plot(self, job):
    u = utils.utils(job)
        
    colors = d3["Category20"][20]

    hc = {}
    for i, hostname in enumerate(u.hostnames):
      hc[hostname] = colors[i%20]
    
    plots = []
    hover = HoverTool(tooltips = [("val", "@y"), ("time", "@x"), ("name", "$name")], 
                      line_policy = "nearest")
    TOOLS = ["pan,wheel_zoom,box_zoom,reset,save,box_select", hover]

    # FLOPS Plot
    try:
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "GFLOPS"

      schema, _stats = u.get_type("pmc")
      vector_widths = {"SSE_D_ALL" : 1, "SIMD_D_256" : 2, 
                       "FP_ARITH_INST_RETIRED_SCALAR_DOUBLE" : 1, 
                       "FP_ARITH_INST_RETIRED_128B_PACKED_DOUBLE" : 2, 
                       "FP_ARITH_INST_RETIRED_256B_PACKED_DOUBLE" : 4, 
                       "FP_ARITH_INST_RETIRED_512B_PACKED_DOUBLE" : 8, 
                       "SSE_DOUBLE_SCALAR" : 1, 
                       "SSE_DOUBLE_PACKED" : 2, 
                       "SIMD_DOUBLE_256" : 4}
      for hostname, stats in _stats.iteritems():
        flops = 0
        for eventname in schema:
          if eventname in vector_widths:
            index = schema[eventname].index
            flops += stats[:, index]*vector_widths[eventname]
        flops = numpy.diff(flops)/numpy.diff(job.times)/1.0e9
        p.step(x = u.hours, y = numpy.append(flops, flops[-1]), 
               mode = "after", line_color = hc[hostname], name = hostname)
      plots += [p]
    except: 
      print("FLOPS plot fails for JOBID", job.id)
      print sys.exc_info()
    
    # Plot MCDRAM BW for KNL    
    try:
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      if u.pmc == 'intel_knl':
        p.yaxis.axis_label = "MCDRAM GB/s"

        imc_schema, imc_stats  = u.get_type("intel_knl_mc_dclk")
        edce_schema, edce_stats = u.get_type("intel_knl_edc_eclk")
        edcu_schema, edcu_stats = u.get_type("intel_knl_edc_uclk")

        for hostname in imc_stats.keys():                      
          rate = edce_stats[hostname][:, edce_schema["RPQ_INSERTS"].index] + \
                     edce_stats[hostname][:, edce_schema["WPQ_INSERTS"].index]
          if not "Flat" in job.acct["queue"]:
            rate -= edcu_stats[hostname][:, edcu_schema["EDC_MISS_CLEAN"].index] + \
                        edcu_stats[hostname][:, edcu_schema["EDC_MISS_DIRTY"].index] + \
                        imc_stats[hostname][:, imc_schema["CAS_READS"].index]
          rate = numpy.diff(rate)/numpy.diff(job.times)*64/(2**30)
          p.step(x = u.hours, y = numpy.append(rate, rate[-1]), 
                 mode = "after", line_color = hc[hostname], name = hostname)
        plots += [p]
    except:
      print('MCDRAM Bandwidth plot failed for jobid ' + job.id )
      print sys.exc_info()

    # Plot DRAM Bandwidth (GB/s)
    try:
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "DRAM GB/s"
      schema, _stats  = u.get_type("imc")
    
      for hostname, stats in _stats.iteritems():               
        rate = stats[:, schema["CAS_READS"].index] + \
                 stats[:, schema["CAS_WRITES"].index]
        rate = numpy.diff(rate)/numpy.diff(job.times)*64/(2**30)
        p.step(x = u.hours, y = numpy.append(rate, rate[-1]), 
               mode = "after", line_color = hc[hostname], name = hostname)
      plots += [p]
    except:
      print('DRAM Bandwidth plot failed for jobid ' + job.id )
      print sys.exc_info()

    # Plot Memory Usage (GB)
    try: 
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "Memory Usage GB"
      schema, _stats = u.get_type("mem")
      for hostname, stats in _stats.iteritems():               
        usage = (stats[:, schema["MemUsed"].index] - \
                 stats[:, schema["Slab"].index] - \
                 stats[:, schema["FilePages"].index])/(2.0**30)
        p.step(x = u.hours, y = usage, mode = "before", line_color = hc[hostname], name = hostname)
      plots += [p]
    except:
      print("Memory Uage plot failed for jobid ", job.id)

    # Plot LNET Bandwidth
    try:      
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "LNET MB/s"
      schema, _stats  = u.get_type("lnet")
    
      for hostname, stats in _stats.iteritems():               
        rate = stats[:, schema["rx_bytes"].index] + \
               stats[:, schema["tx_bytes"].index]
        rate = numpy.diff(rate)/numpy.diff(job.times)/(2**20)
        p.step(x = u.hours, y = numpy.append(rate, rate[-1]), 
               mode = "after", line_color = hc[hostname])
      plots += [p]
    except:
      print('LNET Bandwidth plot failed for jobid ' + job.id )
      print sys.exc_info()

    # Plot IB Bandwidth
    try:      
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "IB MB/s"
      schema, _stats  = u.get_type("ib_sw")
    
      for hostname, stats in _stats.iteritems():               
        rate = stats[:, schema["rx_bytes"].index] + \
               stats[:, schema["tx_bytes"].index]
        rate = numpy.diff(rate)/numpy.diff(job.times)/(2**20)
        p.step(x = u.hours, y = numpy.append(rate, rate[-1]), 
               mode = "after", line_color = hc[hostname], name = hostname)
      plots += [p]
    except:
      print('IB Bandwidth plot failed for jobid ' + job.id )
      print sys.exc_info()

    # Plot OPA Bandwidth
    try:      
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "OPA MB/s"
      schema, _stats  = u.get_type("opa")
      for hostname, stats in _stats.iteritems():               
        rate = stats[:, schema["portRcvData"].index] + \
               stats[:, schema["portXmitData"].index]
        rate = numpy.diff(rate)/numpy.diff(job.times)/125000
        p.step(x = u.hours, y = numpy.append(rate, rate[-1]), 
               mode = "after", line_color = hc[hostname], name = hostname)
      plots += [p]
    except:
      print('OPA Bandwidth plot failed for jobid ' + job.id )
      print sys.exc_info()


    #Plot CPU Usage
    try:      
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "CPU Usage %"
      schema, _stats  = u.get_type("cpu")
      for hostname, stats in _stats.iteritems():               
        busy = stats[:, schema["user"].index] + stats[:, schema["system"].index] + \
               stats[:, schema["nice"].index]
        idle = stats[:, schema["iowait"].index] + stats[:, schema["idle"].index] + \
               stats[:, schema["irq"].index] + stats[:, schema["softirq"].index]
        usage = 100*numpy.diff(busy)/numpy.diff(idle)
        p.step(x = u.hours, y = numpy.append(usage, usage[-1]), 
               mode = "after", line_color = hc[hostname], name = hostname)
      plots += [p]
    except:
      print('CPU Usage plot failed for jobid ' + job.id )
      print sys.exc_info()

    # Plot CPU Frequency
    try:      
      p = figure(plot_height = 150, plot_width = 400, tools = TOOLS)
      p.yaxis.axis_label = "Freq GHz"
      schema, _stats  = u.get_type("pmc")
      for hostname, stats in _stats.iteritems():               
        rate = u.freq*(numpy.diff(stats[:, schema["CLOCKS_UNHALTED_CORE"].index]) / \
                          numpy.diff(stats[:, schema["CLOCKS_UNHALTED_REF"].index]))
        p.step(x = u.hours, y = numpy.append(rate, rate[-1]), 
               mode = "after", line_color = hc[hostname], name = hostname)
      plots += [p]
    except:
      print('CPU Frequency plot failed for jobid ' + job.id )
      print sys.exc_info()

    return gridplot(*plots, ncols = len(plots)/4 + 1, toolbar_options = {"logo" : None})
