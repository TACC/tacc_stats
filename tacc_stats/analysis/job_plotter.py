#!/usr/bin/env python
import sys

import tacc_stats.analysis as analysis
import tacc_stats.analysis.gen.tspl_utils as tspl_utils

def main(**args):
    plot_type = getattr(sys.modules[analysis.__name__],args['plot']) 
    plot = plot_type(processes=args['p'],mode=args['mode'], 
                     header=args['header'],
                     prefix=args['prefix'],outdir=args['o'],
                     aggregate=(not args['full']),wide=args['wide'],
                     save=True)

    filelist=tspl_utils.getfilelist(args['files'])
    plot.run(filelist)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Plot list of jobs')
    parser.add_argument('-p', help='Set number of processes',
                        type=int, default=1)
    parser.add_argument('-files', help='Files to plot',
                        nargs='?', type=str)
    parser.add_argument('-mode', help='Style of plot: lines, percentile',
                        type=str,default='lines')
    parser.add_argument('-header', help='Header of plot',
                        type=str,default='')
    parser.add_argument('-prefix', help='Prefix of plot name',
                        type=str,default='')
    parser.add_argument('-plot', help='Plot type to generate',
                        type=str)
    parser.add_argument('-full', help='Do not aggregate over node',
                        action="store_true")
    parser.add_argument('-o', help='Output directory',
                        type=str, default='.', 
                        metavar='output_dir')
    parser.add_argument('-wide', help='Set wide plot format',
                        action="store_true",default=False)

    main(**vars(parser.parse_args()))

