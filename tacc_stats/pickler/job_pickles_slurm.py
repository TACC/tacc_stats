#!/usr/bin/env python
from __future__ import print_function
import os, sys
from tacc_stats.pickler import job_stats
from datetime import datetime, timedelta
from dateutil.parser import parse
import cPickle as pickle
import multiprocessing, functools
import argparse, csv
import hostlist
from tacc_stats import cfg
from tacc_stats.progress import progress

def test_job(job):
    validated = []
    for host in job.hosts.values():
        if host.marks.has_key('begin %s' % job.id) and host.marks.has_key('end %s' % job.id):
            validated += [True]
        else:
            validated += [False]
    validated = all(validated)
    return validated

def job_pickle(reader_inst,
               pickles_dir, 
               archive_dir,
               host_name_ext = cfg.host_name_ext):

    date_dir = os.path.join(pickles_dir,
                            datetime.fromtimestamp(reader_inst['end_time']).strftime('%Y-%m-%d'))

    try: os.makedirs(date_dir)
    except: pass

    pickle_file = os.path.join(date_dir, reader_inst['id'])

    validated = False
    if os.path.exists(pickle_file):
        try:
            with open(pickle_file) as fd: job = pickle.load(fd)
            validated = test_job(job)
        except EOFError as e:
            print(e)
            
    if not validated:
        job = job_stats.from_acct(reader_inst, archive_dir, '', host_name_ext) 
        if job and test_job(job):
            pickle.dump(job, open(pickle_file, 'w'), pickle.HIGHEST_PROTOCOL)
            validated = True

    return (reader_inst['id'], validated)

class JobPickles:

    def __init__(self, start, end, processes, pickles_dir, jobids):

        self.pool   = multiprocessing.Pool(processes = processes)        
        self.jobids = jobids
        self.start  = start
        self.end    = end

        if not pickles_dir: pickles_dir = cfg.pickles_dir
        self.acct_path = cfg.acct_path
        self.pickles_dir = pickles_dir
        self.partial_pickle = functools.partial(job_pickle,
                                                pickles_dir  = pickles_dir,
                                                archive_dir = cfg.archive_dir)        
        
        print("Use", processes, "processes")
        print("Map node-level data from", cfg.archive_dir, "to", pickles_dir)
        print("From dates:", self.start.date(), "to", self.end.date())
  
    def daterange(self, start_date, end_date):
        date = start_date
        while date <= end_date:
            yield date
            date = date + timedelta(days=1)       

    def run(self):
        for date in self.daterange(self.start, self.end):
            if not os.path.exists(os.path.join(self.acct_path, date.strftime("%Y-%m-%d") + ".txt")): continue
            acct = self.acct_reader(os.path.join(self.acct_path, date.strftime("%Y-%m-%d") + ".txt"))

            try: os.makedirs(os.path.join(self.pickles_dir, date.strftime("%Y-%m-%d")))
            except: pass

            vfile = os.path.join(self.pickles_dir, date.strftime("%Y-%m-%d"), "validated")            
            val_stat = {}
            if os.path.exists(vfile):
                with open(vfile, 'r') as fdv:
                    for line in sorted(list(set(fdv.readlines()))):
                        jobid, stat = line.split()
                        val_stat[jobid] = stat
            ntot = len(acct)
            print(len(acct),'Job records in accounting file')
            acct = [x for x in acct if val_stat.get(x['id']) == "False" or val_stat.get(x['id']) == None]
            print(len(acct),'Jobs to process')
            ntod = len(acct)
            ctr = 0
            with open(vfile, "a+") as fdv:
                for result in self.pool.imap(self.partial_pickle, acct):
                    fdv.write("%s %s\n" % result)
                    fdv.flush()
                    ctr += 1.0
                    progress(ctr+(ntot-ntod), ntot, date.strftime("%Y-%m-%d"))

    def acct_reader(self, filename):
        ftr = [3600,60,1]
        acct = []
        with open(filename, "rb") as fd:
            for job in csv.DictReader(fd, delimiter = '|'):
                if self.jobids and job['JobID'] not in self.jobids: continue
                if job['NodeList'] == "None assigned": continue

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
                jent['host_list']  = hostlist.expand_hostlist(job['NodeList'])

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

    parser.add_argument('start', type = parse, nargs='?', default = datetime.now() - timedelta(days=1), 
                        help = 'Start (YYYY-mm-dd)')
    parser.add_argument('end',   type = parse, nargs='?', default = False, 
                        help = 'End (YYYY-mm-dd)')
    parser.add_argument('-p', '--processes', type = int, default = 1,
                        help = 'number of processes')
    parser.add_argument('-d', '--directory', type = str, 
                        help='Directory to store data')
    parser.add_argument('-jobids', help = 'Pickle this list of jobs', 
                        type = str, nargs = '+')

    args = parser.parse_args()
    print (args)
    if not args.end:
        args.end = args.start + timedelta(days=2)

    pickle_options = { 'processes'       : args.processes,
                       'start'           : args.start,
                       'end'             : args.end,
                       'pickles_dir'     : args.directory,
                       'jobids'          : args.jobids
                       }
    
    pickler = JobPickles(**pickle_options)
    pickler.run()
