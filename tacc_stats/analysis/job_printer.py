#!/usr/bin/env python
import sys, os
import cPickle as pickle
from datetime import datetime
from tacc_stats import cfg as cfg
from tacc_stats.pickler import batch_acct,job_stats

def main(**args):

    acct = batch_acct.factory(cfg.batch_system,
                              cfg.acct_path)
    if args['jobid']:
        reader = acct.find_jobids(args['jobid']).next()    
        date_dir = os.path.join(cfg.pickles_dir,
                                datetime.fromtimestamp(reader['end_time']).strftime('%Y-%m-%d'))
        pickle_file = os.path.join(date_dir, reader['id'])
    else:
        pickle_file = args['file']

    with open(pickle_file) as fd:
        data = pickle.load(fd)

    print "Hosts:", data.hosts.keys()    
    if not args['host']: pass
    elif args['host'] in data.hosts:
        data.hosts = { args['host'] : data.hosts[args['host']] }
    else:
        print args['host'],"does not exist in", args['file']
        return 

        
    for host_name, host in data.hosts.iteritems():
        print "Host:",host_name
        print "Types:",host.stats.keys()
        print host.marks
        if not args['type']: pass
        elif args['type'] in host.stats: 
            host.stats = { args['type'] : host.stats[args['type']] }
        else: 
            print args['type'],"does not exist in", args['file']
            return 

        for type_name, type_device in host.stats.iteritems():
            print ''
            print "Type:", type_name
            print "Schema:", data.get_schema(type_name).keys()
            for device_name, device in type_device.iteritems():
                print "Device:",device_name
                print device

    print 'test'
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Print job using Job ID or pickle file path')
    parser.add_argument('file', help='Pickle file to print',
                        nargs='?', type=str)
    parser.add_argument('-jobid', help='Job ID to print',
                        nargs='+', type=str)
    parser.add_argument('-type', help='Restrict print to this type')
    parser.add_argument('-host', help='Restrict print to this host')
    main(**vars(parser.parse_args()))

