from __future__ import print_function
import os, sys
import tacc_stats.analysis.plot as plots

### Test plotters
filelist = [os.path.join(os.path.dirname(os.path.abspath(__file__)),'3620_ref')]
print(filelist)
#### MemUsage plotter

#### MemUsage plotter
def mem_test():
    mu_plot = plots.MemUsage(outdir='.',
                             prefix='MemUsage',
                             header='Plot all events for a device',lariat_data='pass',
                             save=True)
    mu_plot.plot(filelist[0])
    assert os.path.isfile(mu_plot.outdir+'/'+mu_plot.fname+'.pdf')
    os.remove(mu_plot.fname+'.pdf')

#### Test device level plotter
def dev_test():
    dev_plot = plots.DevPlot({'intel_hsw' : ['mem']}, {'intel_hsw' : ['MemUsed']},
                             outdir='.',
                             prefix='MemUsed',
                             header='Plot all events for a device',lariat_data='pass',
                             save=True)
    dev_plot.plot(filelist[0])
    assert os.path.isfile(dev_plot.outdir+'/'+dev_plot.fname+'.pdf')
    os.remove(dev_plot.fname+'.pdf')
#### Heat Map plotter
def heat_test():
    heat_plot = plots.HeatMap({'intel_hsw' : ['intel_hsw','intel_hsw']}, 
                              {'intel_hsw' : ['CLOCKS_UNHALTED_REF','INSTRUCTIONS_RETIRED']},
                              outdir='.',
                              prefix='CPI',
                              header='Heat map of CPI',lariat_data='pass',
                              save=True)
    heat_plot.plot(filelist[0])
    assert os.path.isfile(heat_plot.outdir+'/'+heat_plot.fname+'.pdf')
    os.remove(heat_plot.fname+'.pdf')
### MasterPlot test
def masterplot_test():
    plotter = plots.MasterPlot(mode='lines',
                               outdir='.',
                               prefix='imbalance',
                               header='Potentially Imbalanced',lariat_data='pass',
                               wide=True,save=True)
    plotter.plot(filelist[0])
    assert os.path.isfile(plotter.outdir+'/'+plotter.fname+'.pdf')
    os.remove(plotter.fname+'.pdf')
    plotter.mode='percentile'
    plotter.header='Potentially Imbalanced (%)'
    plotter.plot(filelist[0])
    assert os.path.isfile(plotter.outdir+'/'+plotter.fname+'.pdf')
    os.remove(plotter.fname+'.pdf')
    plotter.mode='lines'
    plotter.prefix='step'
    plotter.header='Step Function Performance'
    plotter.plot(filelist[0])
    assert os.path.isfile(plotter.outdir+'/'+plotter.fname+'.pdf')
    os.remove(plotter.fname+'.pdf')
