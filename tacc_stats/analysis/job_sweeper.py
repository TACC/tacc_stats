#!/usr/bin/env python
import argparse,os,sys
from subprocess import Popen, PIPE, call

import tacc_stats.analysis as analysis
import tacc_stats.analysis.gen.tspl_utils as tspl_utils

from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import FigureCanvasPdf as FigureCanvas

from numpy import log,isnan

def main(args):

    print args
    test_type = getattr(sys.modules[analysis.__name__],args.test)
    
    test = test_type(processes=args.p[0], threshold=args.t[0], 
                     min_time=args.s[0], min_hosts=args.N[0],
                     waynesses=args.waynesses, aggregate=args.a)

    print 'Run test '+ test_type.__name__+' for date >>>' 

    failed = test.date_sweep(args.start[0],args.end[0])

    if args.plot:
        plotter = plots.MasterPlot(header='Failed test: '+ test_type.__name__,
                                   prefix=test_type.__name__,outdir=args.o[0],
                                   processes=args.p[0],threshold=args.t[0],
                                   wide=args.wide,save=True)
        plotter.run(failed)

        vals = [v[2] for j,v in test.su.items()]
        vals = [val for val in vals if not isnan(val)]
        fig = Figure()
        ax = fig.add_subplot(1,1,1)
        ax.hist(vals,max(5,5*log(len(vals))))
        ax.set_title("Histogram for test: " + test_type.__name__)
        canvas = FigureCanvas(fig)
        fig.savefig("histogram-"+test_type.__name__+"-"+args.start[0]+"."+args.end[0]+".png")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run tests for jobs')
    parser.add_argument('-start', help='Start date',
                        nargs=1, type=str)
    parser.add_argument('-end', help='End date',
                        nargs=1, type=str)
    parser.add_argument('-p', help='Set number of processes',
                        nargs=1, type=int, default=[1])
    parser.add_argument('-N', help='Set minimum number of hosts',
                        nargs=1, type=int, default=[1])
    parser.add_argument('-s', help='Set minimum time in seconds',
                        nargs=1, type=int, default=[3600])
    parser.add_argument('-t', help='Set test threshold',
                        nargs=1, type=float, default=[1.0])
    parser.add_argument('-test', help='Test to run',
                        nargs='?', type=str)
    parser.add_argument('-waynesses', help='Wayness required',
                        nargs='?', type=int, default=[x+1 for x in range(32)])
    parser.add_argument('-a', help='Aggregate over node', default=True)
    parser.add_argument('-o', help='Output directory',
                        nargs=1, type=str, default=['.'], metavar='output_dir')
    parser.add_argument('-wide', help='Set wide plot format',
                        action="store_true")
    parser.add_argument('-plot', help='Generate a plot',action="store_true")

    main(parser.parse_args())
