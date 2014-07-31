#!/usr/bin/env python
import sys
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import FigureCanvasPdf as FigureCanvas
from numpy import log,isnan
import tacc_stats.analysis.exam as exam
import tacc_stats.analysis.plot as plot
import tacc_stats.cfg as cfg

def main(**args):

    print args
    test_type = getattr(sys.modules[exam.__name__],args['test'])
    
    test = test_type(processes=args['p'], threshold=args['t'], 
                     min_time=args['s'], min_hosts=args['N'],
                     waynesses=args['waynesses'], aggregate=args['a'],
                     ignore_status=args['ignore_status'])

    print 'Running test: '+ test_type.__name__

    failed = test.date_sweep(args['start'],args['end'],pickles_dir = args['dir'])

    if args['plot']:
        plotter = plot.MasterPlot(header='Failed test: '+ test_type.__name__,
                                  prefix=test_type.__name__,outdir=args['o'],
                                  processes=args['p'],threshold=args['t'],
                                  wide=args['wide'],save=True)
        plotter.run(failed)

        vals = [v['metric'] for j,v in test.results.items()]
        vals = [val for val in vals if not isnan(val)]
        fig = Figure()
        ax = fig.add_subplot(1,1,1)
        ax.hist(vals,max(5,5*log(len(vals))))
        ax.set_title("Histogram for test: " + test_type.__name__)
        canvas = FigureCanvas(fig)
        fig.savefig("histogram-"+test_type.__name__+"-"+args['start']+"."+args['end']+".pdf")
    return failed

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run tests for jobs')
    parser.add_argument('-dir', help='Pickles Directory',
                        type=str, default=cfg.pickles_dir)
    parser.add_argument('start', help='Start date',
                        type=str,default='')
    parser.add_argument('end', help='End date',
                        type=str,default='')
    parser.add_argument('-p', help='Set number of processes',
                        type=int, default=1)
    parser.add_argument('-N', help='Set minimum number of hosts',
                        type=int, default=1)
    parser.add_argument('-s', help='Set minimum time in seconds',
                        type=int, default=3600)
    parser.add_argument('-t', help='Set test threshold',
                        type=float, default=1.0)
    parser.add_argument('-test', help='Test to run',
                        type=str, default='Idle')
    parser.add_argument('-ignore_status', help='Status types to ignore',
                        nargs='?', type=str, default=[])
    parser.add_argument('-waynesses', help='Wayness required',
                        nargs='?', type=int, default=[x+1 for x in range(32)])
    parser.add_argument('-a', help='Aggregate over node', default=True)
    parser.add_argument('-o', help='Output directory',
                        type=str, default='.', metavar='output_dir')
    parser.add_argument('-wide', help='Set wide plot format',
                        action="store_true")
    parser.add_argument('-plot', help='Generate a plot',
                        action="store_true")

    main(**vars(parser.parse_args()))
