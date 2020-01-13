#!/usr/bin/env python
import os, sys
from tacc_stats.pickler import job_stats
from datetime import datetime, timedelta
from dateutil.parser import parse
import pickle as p
import multiprocessing, functools
import argparse, csv
import hostlist
from tacc_stats.daterange import daterange
from tacc_stats import cfg
from tacc_stats.progress import progress
from fcntl import flock, LOCK_EX, LOCK_NB

def test_job(job):
    validated = []
    for host in job.hosts.values():
        if "begin %s" % job.id in host.marks and "end %s" % job.id in host.marks:
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
            with open(pickle_file, 'rb') as fd: 
                try: 
                    job = p.load(fd)
                except MemoryError as e:
                    print(e)
                    return (reader_inst['id'], validated)
                except UnicodeDecodeError as e: 
                    try:
                        job = p.load(fd, encoding = "latin1") # Python2 Compatibility
                    except: 
                        print(e)
                        return (reader_inst['id'], validated)
                except:
                    return (reader_inst['id'], validated)
            validated = test_job(job)
        except EOFError as e:
            print(e)
            
    if not validated:
        job = job_stats.from_acct(reader_inst, archive_dir, '', host_name_ext) 
        print("processed jobid ",reader_inst['id'])
        if job and test_job(job):
            try:
                with open(pickle_file, 'wb') as fd: p.dump(job, fd, protocol = p.HIGHEST_PROTOCOL)
            except MemoryError as e:
                print(e)
                return (reader_inst['id'], validated)
            except: return (reader_inst['id'], validated)
            validated = True
    
    return (reader_inst['id'], validated)

class JobPickles:

    def __init__(self, pickles_dir, processes, jobids):

        self.pool   = multiprocessing.Pool(processes = processes)        
        self.jobids = jobids

        self.acct_path = cfg.acct_path
        self.pickles_dir = pickles_dir
        self.partial_pickle = functools.partial(job_pickle,
                                                pickles_dir  = pickles_dir,
                                                archive_dir = cfg.archive_dir)        
        print("Use", processes, "processes")
        print("Map node-level data from", cfg.archive_dir, "to", pickles_dir)

    def run(self, date):
        print("Processing for ", date)
        if not os.path.exists(os.path.join(self.acct_path, date.strftime("%Y-%m-%d") + ".txt")): 
            print("No accounting file for ", date)
            return

        acct = self.acct_reader(os.path.join(self.acct_path, date.strftime("%Y-%m-%d") + ".txt"))
        try: 
            os.makedirs(os.path.join(self.pickles_dir, date.strftime("%Y-%m-%d")))
        except: pass

        val_file = os.path.join(self.pickles_dir, date.strftime("%Y-%m-%d"), "validated")            
        val_jids = []
        if os.path.exists(val_file):
            with open(val_file, 'r') as fd:
                val_jids = fd.read().splitlines()

        acct_jids = [x['id'] for x in acct if "+" not in x['id']]

        ntot = len(acct_jids)
        print(len(acct_jids),'Job records in accounting file')
        if self.jobids:
            acct_jids += self.jobids
        run_jids = sorted(list(set(acct_jids) - set(val_jids)))

        print('Jobs to process: ', len(run_jids), run_jids)
        ntod = len(run_jids)

        acct = [job for job in acct if job['id'] in run_jids]            

        if not self.jobids:
            acct = [job for job in acct if job['nodes']*(job['end_time']-job['start_time']) < 88473600]
        ctr = 0
        with open(val_file, "a") as fd:
            for result in self.pool.imap(self.partial_pickle, acct):
            #for result in map(self.partial_pickle, acct):
                if result[1]:
                    fd.write("%s\n" % result[0])
                fd.flush()
                ctr += 1.0
                progress(ctr + (ntot - ntod), ntot, date.strftime("%Y-%m-%d"))
        print("Completed ", date)

    def acct_reader(self, filename):
        ftr = [3600,60,1]
        acct = []
        with open(filename) as fd:
            for job in csv.DictReader(fd, delimiter = '|'):
                if self.jobids and job['JobID'] not in self.jobids: continue
                if job['NodeList'] == "None assigned": continue
                if len(job) != 13: 
                    print(job['JobID'] + " is not parsed correctly")
                    continue
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

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                           "job_pickles_lock"), "w") as fd:
        try:
            flock(fd, LOCK_EX | LOCK_NB)
        except IOError:
            print("job_pickles is already running")
            sys.exit()
        

    parser = argparse.ArgumentParser(description='Run pickler for jobs')
    parser.add_argument('start', type = parse, nargs='?', default = datetime.now(), 
                        help = 'Start (YYYY-mm-dd)')
    parser.add_argument('end',   type = parse, nargs='?', default = False, 
                        help = 'End (YYYY-mm-dd)')
    parser.add_argument('-p', '--processes', type = int, default = 1,
                        help = 'number of processes')
    parser.add_argument('-d', '--directory', type = str, 
                        help='Directory to store data', default = cfg.pickles_dir)
    parser.add_argument('-jobids', help = 'Pickle this list of jobs', 
                        type = str, nargs = '+')

    args = parser.parse_args()
    start = args.start
    end   = args.end
    if not end: end = start

    for date in daterange(start, end):
        pickler = JobPickles(args.directory, args.processes, args.jobids)
        pickler.run(date)
