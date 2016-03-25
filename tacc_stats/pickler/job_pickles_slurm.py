#!/usr/bin/env python
from __future__ import print_function
import os, sys
from ConfigParser import SafeConfigParser
from tacc_stats import cfg
from tacc_stats.pickler import job_stats, acct_reader
from datetime import datetime, timedelta
from dateutil.parser import parse
import cPickle as pickle
import multiprocessing, functools
import argparse, csv

def job_pickle(reader_inst, 
               pickles_dir, 
               archive_dir):

    date_dir = os.path.join(pickles_dir,
                            datetime.fromtimestamp(reader_inst['end_time']).strftime('%Y-%m-%d'))
    try: os.makedirs(date_dir)
    except: pass

    pickle_file = os.path.join(date_dir, reader_inst['id'])

    validated = False
    if os.path.exists(pickle_file):
        validated = True
        with open(pickle_file) as fd:
            try:
                job = pickle.load(fd)
                for host in job.hosts.values():
                    if not host.marks.has_key('begin %s' % job.id) or not host.marks.has_key('end %s' % job.id):
                        validated = False
                        break
            except: 
                validated = False

    if not validated:
        print(reader_inst['id'] + " is not validated: process")
        with open(pickle_file, 'w') as fd:
            job = job_stats.from_acct(reader_inst, archive_dir, '', '') 
            if job: pickle.dump(job, fd, pickle.HIGHEST_PROTOCOL)
    else:
        print(reader_inst['id'] + " is validated: do not process")

class JobPickles:

    def __init__(self, start, end, processes, pickles_dir):

        self.pool   = multiprocessing.Pool(processes = processes)        

        self.start  = start
        self.end    = end
        if not pickles_dir:
            pickles_dir = cfg.pickles_dir            

        self.partial_pickle = functools.partial(job_pickle,
                                                pickles_dir  = pickles_dir,
                                                archive_dir = cfg.archive_dir)
        print("Use", processes, "processes")
        print("Map node-level data from", cfg.archive_dir,"to",pickles_dir)
        print("From dates:", self.start.date(), "to", self.end.date())
  
    def daterange(self, start_date, end_date):
        date = start_date
        while date <= end_date:
            yield date
            date = date + timedelta(days=1)       


    def run(self):
        acct = []
        for date in self.daterange(self.start, self.end):
            acct = self.acct_reader(os.path.join(cfg.acct_path, date.strftime("%Y-%m-%d") + ".txt"))
            self.pool.map(self.partial_pickle, acct)

    def acct_reader(self, filename):
        ftr = [3600,60,1]
        acct = []
        with open(filename, "rb") as fd:
            for job in csv.DictReader(fd, delimiter = '|'):
                nodelist_str = job['NodeList']
                if '[' in nodelist_str and ']' in nodelist_str:
                    nodelist = []
                    prefix, nids = nodelist_str.rstrip("]").split("[")
                    for nid in nids.split(','):
                        if '-' in nid:
                            bot, top = nid.split('-')
                            nodelist += range(int(bot), int(top)+1)
                        else: nodelist += [nid]
                    zfac = len(str(max(nodelist)))
                    nodelist = [prefix + str(x).zfill(zfac) for x in nodelist]
                    job['NodeList'] = nodelist
                else:
                    job['NodeList'] = [nodelist_str]

                jent = {}
                jent['id']         = job['JobID']
                jent['user']       = job['User']
                jent['project']    = job['Account']
                jent['start_time'] = int(parse(job['Start']).strftime('%s'))
                jent['end_time']   = int(parse(job['End']).strftime('%s'))
                jent['queue_time'] = int(parse(job['Submit']).strftime('%s'))
                jent['queue']      = job['Partition']
                jent['name']       = job['JobName']
                jent['status']     = job['State'].split()[0]
                jent['nodes']      = int(job['NNodes'])
                jent['cores']      = int(job['ReqCPUS'])
                jent['host_list']  = job['NodeList']

                if '-' in job['Timelimit']:
                    days, time = job['Timelimit'].split('-')
                else:
                    time = job['Timelimit']
                    days = 0
                jent['requested_time'] = (int(days) * 86400 + 
                                          sum([a*b for a,b in zip(ftr, [int(i) for i in time.split(":")])]))/60
                acct += [jent]
            return acct

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run pickler for jobs')
    parser.add_argument('start', type = parse, default = datetime.now() - timedelta(days=1), 
                        help = 'Start (YYYY-mm-dd)')
    parser.add_argument('end',   type = parse, nargs = '?', default = False, 
                        help = 'End (YYYY-mm-dd)')
    parser.add_argument('-p', '--processes', type = int, default = 1,
                        help = 'number of processes')
    parser.add_argument('-d', '--directory', type = str, 
                        help='Directory to store data')
    args = parser.parse_args()
    if not args.end:
        args.end = args.start + timedelta(days=1)

    pickle_options = { 'processes'       : args.processes,
                       'start'           : args.start,
                       'end'             : args.end,
                       'pickles_dir'      : args.directory,
                       }
    
    pickler = JobPickles(**pickle_options)
    pickler.run()
