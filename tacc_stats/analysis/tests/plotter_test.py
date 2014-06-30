from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis.job_plotter as plotter

### Test plotters
filelist = os.path.join(os.path.dirname(os.path.abspath(__file__)),'../plot/tests','1835740_ref')

def plotter_test():
    args = {'files': filelist, 'plot': 'MasterPlot', 'full': False, 'header': '', 'o': '.', 'p': 1, 'prefix': '', 'mode': 'lines', 'wide': False}

    plotter.main(**args)
    assert os.path.isfile(args['o']+'/_1835740_809035_master'+'.pdf') or os.path.isfile(args['o']+'/_1835740_r_tsyshe_master'+'.pdf')

    try: os.remove('_1835740_809035_master'+'.pdf')
    except: os.remove('_1835740_r_tsyshe_master'+'.pdf')

