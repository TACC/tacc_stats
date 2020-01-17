#!/usr/bin/env python
import os,sys, pwd
from datetime import timedelta, datetime
from dateutil.parser import parse
from fcntl import flock, LOCK_EX, LOCK_NB
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
import django
django.setup()
from tacc_stats.site.machine.models import Job, Host, Libraries
from tacc_stats.site.xalt.models import run, join_run_object, lib
from tacc_stats.analysis.metrics import metrics
import tacc_stats.cfg as cfg
from tacc_stats.progress import progress
from tacc_stats.daterange import daterange
import pytz, calendar
import pickle as p
import traceback
import csv
import hostlist

def update_acct(date, rerun = False):
    ftr = [3600,60,1]
    tz = pytz.timezone('US/Central')
    ctr = 0

    with open(os.path.join(cfg.acct_path, date.strftime("%Y-%m-%d") + '.txt'), encoding = "latin1") as fd:
        nrecords = sum(1 for record in csv.DictReader(fd))
        fd.seek(0)
        
        for job in csv.DictReader(fd, delimiter = '|'):
            if '+' in job['JobID']: 
                jid, rid = job['JobID'].split('+')
                job['JobID'] = int(jid) + int(rid)

            if rerun: 
                pass
            elif Job.objects.filter(id = job['JobID']).exists(): 
                ctr += 1
                continue                
            json = {}

            json['id']          = job['JobID']
            json['project']     = job['Account']
            json['start_time']  = tz.localize(parse(job['Start']))
            json['end_time']    = tz.localize(parse(job['End']))
            json['start_epoch'] = calendar.timegm(json['start_time'].utctimetuple())
            json['end_epoch']   = calendar.timegm(json['end_time'].utctimetuple())
            json['run_time'] = json['end_epoch'] - json['start_epoch']

            try:
                if '-' in job['Timelimit']:
                    days, time = job['Timelimit'].split('-')
                else:
                    time = job['Timelimit']
                    days = 0
                json['requested_time'] = (int(days) * 86400 +
                                          sum([a*b for a,b in zip(ftr, [int(i) for i in time.split(":")])]))/60
            except: pass

            json['queue_time'] = int(parse(job['Submit']).strftime('%s'))
            try:
                json['queue']      = job['Partition']
                json['name']       = job['JobName'][0:128]
                json['status']     = job['State'].split()[0]
                json['nodes']      = int(job['NNodes'])
                json['cores']      = int(job['ReqCPUS'])
                json['wayness']    = json['cores']/json['nodes']
                json['date']       = json['end_time'].date()
                json['user']       = job['User']
            except:
                print(job)
                continue
            if "user" in json:
                try: 
                    json['uid'] = int(pwd.getpwnam(json['user']).pw_uid)
                except: pass

            host_list = hostlist.expand_hostlist(job['NodeList'])
            del job['NodeList']

            Job.objects.filter(id=json['id']).delete()
            try:
                obj, created = Job.objects.update_or_create(**json)
            except:
                continue
            ### If xalt is available add data to the DB 
            xd = None
            try: 
                #xd = run.objects.using('xalt').filter(job_id = json['id'])[0]
                for r in run.objects.using('xalt').filter(job_id = json['id']):
                    if "usr" in r.exec_path.split('/'): continue
                    xd = r
            except: pass
            
            if xd:            
                obj.exe  = xd.exec_path.split('/')[-1][0:128]
                obj.exec_path = xd.exec_path
                obj.cwd     = xd.cwd[0:128]
                obj.threads = xd.num_threads
                obj.save()
                for join in join_run_object.objects.using('xalt').filter(run_id = xd.run_id):
                    object_path = lib.objects.using('xalt').get(obj_id = join.obj_id).object_path
                    module_name = lib.objects.using('xalt').get(obj_id = join.obj_id).module_name
                    if not module_name: module_name = 'none'
                    library = Libraries(object_path = object_path, module_name = module_name)
                    library.save()
                    library.jobs.add(obj)

            ### Build host table
            for host_name in host_list:
                h = Host(name=host_name)
                h.save()
                h.jobs.add(obj)

            ctr += 1
            progress(ctr, nrecords, date)
    try:
        with open(os.path.join(cfg.pickles_dir, date.strftime("%Y-%m-%d"), "validated")) as fd:
            for line in fd.readlines():
                Job.objects.filter(id = int(line)).update(validated = True)
    except: pass
def update_metrics(date, pickles_dir, processes, rerun = False):

    min_time = 60
    metric_names = [
        "avg_ethbw", "avg_cpi", "avg_freq", "avg_loads", "avg_l1loadhits",
        "avg_l2loadhits", "avg_llcloadhits", "avg_sf_evictrate", "max_sf_evictrate", 
        "avg_mbw", "avg_page_hitrate", "time_imbalance",
        "mem_hwm", "max_packetrate", "avg_packetsize", "node_imbalance",
        "avg_flops_32b", "avg_flops_64b", "avg_vector_width_32b", "vecpercent_32b", "avg_vector_width_64b", "vecpercent_64b", 
        "avg_cpuusage", "max_mds", "avg_lnetmsgs", "avg_lnetbw", "max_lnetbw", "avg_fabricbw",
        "max_fabricbw", "avg_mdcreqs", "avg_mdcwait", "avg_oscreqs",
        "avg_oscwait", "avg_openclose", "avg_mcdrambw", "avg_blockbw", "max_load15"
    ]

    aud = metrics.Metrics(metric_names, processes = processes)

    print("Run the following tests for:",date)
    for name in aud.metric_list:
        print(name)

    jobs_list = Job.objects.filter(date = date).exclude(run_time__lt = min_time)

    # Use avg_cpuusage to see if job was tested.  It will always exist
    if not rerun:
        jobs_list = jobs_list.filter(avg_vector_width_32b = None)

    paths = []
    for job in jobs_list:
        paths.append(os.path.join(pickles_dir,
                                  job.date.strftime("%Y-%m-%d"),
                                  str(job.id)))
        
    num_jobs = jobs_list.count()
    print("# Jobs to be tested:",num_jobs)
    if num_jobs == 0 : return

    for jobid, metric_dict in aud.run(paths):
        try:
            if metric_dict: jobs_list.filter(id = jobid).update(**metric_dict)
        except: pass

if __name__ == "__main__":
    import argparse
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "update_db_lock"), "w") as fd:
        try:
            flock(fd, LOCK_EX | LOCK_NB)
        except IOError:
            print("update_db is already running")
            sys.exit()

    parser = argparse.ArgumentParser(description='Run database update')

    parser.add_argument('start', type = parse, nargs='?', default = datetime.now(), 
                        help = 'Start (YYYY-mm-dd)')
    parser.add_argument('end',   type = parse, nargs='?', default = False, 
                        help = 'End (YYYY-mm-dd)')
    parser.add_argument('-p', '--processes', type = int, default = 1,
                        help = 'number of processes')
    parser.add_argument('-d', '--directory', type = str, 
                        help='Directory to read data', default = cfg.pickles_dir)

    args = parser.parse_args()    
    start = args.start
    end   = args.end
    if not end: end = start

    for date in daterange(start, end):
        update_acct(date, rerun = False)         
        update_metrics(date, args.directory, args.processes, rerun = False)
