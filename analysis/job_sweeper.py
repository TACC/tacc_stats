#!/usr/bin/env python
import argparse,os,sys
from subprocess import Popen, PIPE, call

import datetime
sys.path.append(os.path.join(os.path.dirname(__file__),
                             '../lib'))
import analysis.exam.tests as tests
import analysis.plot.plots as plots
import analysis.gen.tspl_utils as tspl_utils
import sys_conf

path = sys_conf.pickles_dir

def sweep(test,start,end):
    for date in os.listdir(path):
        try:
            s = [int(x) for x in start.split('-')]
            e = [int(x) for x in end.split('-')]
            d = [int(x) for x in date.split('-')]
        except: continue
        if not datetime.date(s[0],s[1],s[2]) <= datetime.date(d[0],d[1],d[2]) <= datetime.date(e[0],e[1],e[2]): 
            continue
        print '>>>',date
        files = os.path.join(path,date)
        filelist=tspl_utils.getfilelist(files)
        test.run(filelist)

    print 'Failed jobs'
    print test.top_jobs()    
    return test.failed()

def main():

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
    parser.add_argument('-wide', help='Set wide plot format',default=True)
    parser.add_argument('-plot', help='Generate a plot',default=True)
    parser.add_argument('-save', help='Save a plot',default=True)
    args=parser.parse_args()

    import inspect
    for name, obj in inspect.getmembers(tests):
        if hasattr(obj,"__bases__") and tests.Test in obj.__bases__:            
            if args.test in obj.__name__:
                test = obj(processes=args.p[0], threshold=args.t[0], 
                           min_time=args.s[0], min_hosts=args.N[0],
                           waynesses=args.waynesses, aggregate=args.a)
                print 'Run test '+ obj.__name__+' for date >>>' 
                failed = sweep(test,args.start[0],args.end[0])
                print failed
                if args.plot:
                    plotter = plots.MasterPlot(header='Failed test: '+ obj.__name__,
                                               prefix=obj.__name__,outdir=args.o[0],
                                               processes=args.p[0],threshold=args.t[0],
                                               wide=args.wide,save=args.save)
                    plotter.run(failed)

if __name__ == '__main__':
    main()
