#!/usr/bin/env python
import sys,os,pwd
import operator
import cPickle as pickle
from datetime import datetime,timedelta
import tacc_stats.analysis.exam as exam
import tacc_stats.analysis.plot as plot
import tacc_stats.cfg as cfg
from tacc_stats.analysis.gen import tspl,tspl_utils
from tacc_stats.pickler import job_stats, batch_acct
from numpy import diff

def main(**args):
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
        
    for f in filelist:
        with open(f) as fd:
            if args['a']:       
                data = pickle.load(fd)
                data = diff(data.aggregate_stats(args['type']))/diff(data.times)
                print data

    if not args['plot']: return

    plot_type = getattr(sys.modules[plots.__name__],args['plot'])
    plot = plot_type(processes=args['p'],mode=args['mode'],
                     header=args['header'],
                     prefix=args['prefix'],outdir=args['o'],
                     aggregate=(not args['full']),wide=args['wide'],
                     save=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compute a metric for jobs')
    parser.add_argument('-jobids', help='Job IDs to plot',
                        nargs='+', type=str)
    parser.add_argument('-type', help='Type of Device', type=str)
    parser.add_argument('-stat', help='Type of Stat', type=str)
    parser.add_argument('-dir', help='Pickles Directory',
                        type=str, default=cfg.pickles_dir)
    parser.add_argument('-a', help='Aggregate over devices', default=True)
    parser.add_argument('-device', help='Aggregate over devices', default=None)
    parser.add_argument('-plot', help='Generate a plot',
                        action="store_true")

    main(**vars(parser.parse_args()))
