#!/usr/bin/env python
import sys, os
from datetime import datetime
from tacc_stats import cfg as cfg
import tacc_stats.analysis.plot as plots
import tacc_stats.analysis.gen.tspl_utils as tspl_utils
from tacc_stats.pickler import batch_acct

def main(**args):
    plot_type = getattr(sys.modules[plots.__name__],args['plot']) 
    plot = plot_type(processes=args['p'],mode=args['mode'], 
                     header=args['header'],
                     prefix=args['prefix'],outdir=args['o'],
                     aggregate=(not args['full']),wide=args['wide'],
                     save=True)

    try:
        batch_system = args.get('batch_system',cfg.batch_system)
        acct_path = args.get('acct_path',cfg.acct_path)
        host_name_ext = args.get('host_name_ext',cfg.host_name_ext)
        
        acct = batch_acct.factory(batch_system,
                                  acct_path,
                                  host_name_ext)
        reader = acct.find_jobids(args['jobids'])
        filelist = []
        for acct in reader:
            date_dir = os.path.join(cfg.pickles_dir,
                                    datetime.fromtimestamp(acct['end_time']).strftime('%Y-%m-%d'))
            filelist.append(os.path.join(date_dir,acct['id']))

    except:
        filelist = tspl_utils.getfilelist(args['files'])

    plot.run(filelist)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Plot list of jobs')
    parser.add_argument('-p', help='Set number of processes',
                        type=int, default=1)
    parser.add_argument('files', help='Files to plot',
                        nargs='?', type=str)
    parser.add_argument('-jobids', help='Job IDs to plot',
                        nargs='+', type=str)
    parser.add_argument('-mode', help='Style of plot: lines, percentile',
                        type=str,default='lines')
    parser.add_argument('-header', help='Header of plot',
                        type=str,default='')
    parser.add_argument('-prefix', help='Prefix of plot name',
                        type=str,default='')
    parser.add_argument('-plot', help='Plot type to generate',
                        type=str,default='MasterPlot')
    parser.add_argument('-full', help='Do not aggregate over node',
                        action="store_true")
    parser.add_argument('-o', help='Output directory',
                        type=str, default='.', 
                        metavar='output_dir')
    parser.add_argument('-wide', help='Set wide plot format',
                        action="store_true",default=False)

    main(**vars(parser.parse_args()))

