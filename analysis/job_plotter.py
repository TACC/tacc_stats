#!/usr/bin/env python
import argparse,os,sys
from subprocess import Popen, PIPE, call
from collections import Counter
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

        c = Counter(test.results.values())
        print "---------------------------------------------"
        try: 
            print "Jobs tested:",c[True]+c[False]
            print "Percentage of jobs failed:",100*c[True]/float(c[True]+c[False])
        except ZeroDivisionError: 
            print "No jobs failed."
            return
    print 'Failed jobs'
    for x in test.top_jobs():
        print x[0],x[1]
    return test.failed()

def main():

    parser = argparse.ArgumentParser(description='Plot list of jobs')
    parser.add_argument('-p', help='Set number of processes',
                        nargs=1, type=int, default=[1])
    parser.add_argument('-files', help='Files to plot',
                        nargs='?', type=str)
    parser.add_argument('-mode', help='Style of plot: lines, percentile',
                        nargs=1, type=str,default=['lines'])
    parser.add_argument('-header', help='Header of plot',
                        nargs=1, type=str,default=[''])
    parser.add_argument('-prefix', help='Prefix of plot name',
                        nargs=1, type=str,default=[''])
    parser.add_argument('-plot', help='Plot type to generate',
                        nargs='?', type=str)
    parser.add_argument('-a', help='Aggregate over node', default=True)
    parser.add_argument('-o', help='Output directory',
                        nargs=1, type=str, default=['.'], metavar='output_dir')
    parser.add_argument('-wide', help='Set wide plot format',
                        action="store_true")

    args=parser.parse_args()
    print args
    import inspect
    for name, obj in inspect.getmembers(plots):
        if hasattr(obj,"__bases__") and plots.Plot in obj.__bases__:            
            if args.plot in obj.__name__:
                plot = obj(processes=args.p[0],mode=args.mode[0], 
                           header=args.header[0],
                           prefix=args.prefix[0],outdir=args.o[0],
                           aggregate=args.a,save=True)

                filelist=tspl_utils.getfilelist(args.files)
                plot.run(filelist)

if __name__ == '__main__':
    main()
