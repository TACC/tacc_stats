#!/usr/bin/env python
import os,sys, pwd
from datetime import timedelta, datetime
from dateutil.parser import parse
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
import django
django.setup()
from tacc_stats.site.machine.models import Job, Host, Libraries, TestInfo
from tacc_stats.site.xalt.models import run, join_run_object, lib
from tacc_stats.analysis import exam
import tacc_stats.cfg as cfg
from tacc_stats.progress import progress
from tacc_stats.daterange import daterange
import pytz, calendar
import cPickle as pickle
import traceback
import csv
import hostlist

def update_comp_info(thresholds = None):
    
    schema_map = {'HighCPI' : ['cpi','>',1.5], 
                  'HighCPLD' : ['cpld','>',1.5], 
                  'Load_L1Hits' : ['Load_L1Hits','>',1.5], 
                  'Load_L2Hits' : ['Load_L2Hits','>',1.5], 
                  'Load_LLCHits' : ['Load_LLCHits','>',1.5], 
                  'MemBw' : ['mbw', '<', 1.0 ],
                  'Catastrophe' : ['cat', '<',0.01] ,
                  'MemUsage' : ['mem','>',31], 
                  'PacketRate' : ['packetrate','>',0], 
                  'PacketSize' : ['packetsize','>',0],
                  'Idle' : ['idle','>',0.99],
                  'LowFLOPS' : ['flops','<',10],
                  'VecPercent' : ['VecPercent','<',0.05],
                  'GigEBW' : ['GigEBW','>',1e7],
                  'CPU_Usage' : ['CPU_Usage','<',800],
                  'MIC_Usage' : ['MIC_Usage','>',0.0],
                  'Load_All' : ['Load_All','<',1e7],
                  'MetaDataRate' : ['MetaDataRate','>',10000],
                  'InternodeIBAveBW' : ['InternodeIBAveBW', '>', 10000],
                  'InternodeIBMaxBW' : ['InternodeIBMaxBW', '>', 10000],
                  'LnetAveBW'  : ['LnetAveBW', '>', 10000],
                  'LnetAveMsgs'  : ['LnetAveMsgs', '>', 10000],
                  'LnetMaxBW'  : ['LnetMaxBW', '>', 10000],
                  'MDCReqs'  : ['MDCReqs', '>', 10000],
                  'OSCReqs'  : ['OSCReqs', '>', 10000],
                  'OSCWait'  : ['OSCWait', '>', 10000],
                  'MDCWait'  : ['MDCWait', '>', 10000],
                  'LLiteOpenClose'  : ['LLiteOpenClose', '>', 10000],
                  }
    if thresholds:
        for key,val in thresholds.iteritems():
            schema_map[key][1:3] = val

    for name in schema_map:
        if TestInfo.objects.filter(test_name = name).exists():
            TestInfo.objects.filter(test_name = name).delete()

        obj = TestInfo(test_name = name, 
                       field_name = schema_map[name][0], 
                       comparator = schema_map[name][1], 
                       threshold = schema_map[name][2])
        obj.save()

def update_acct(date, rerun = False):
    ftr = [3600,60,1]
    tz = pytz.timezone('US/Central')
    ctr = 0
    with open(os.path.join(cfg.acct_path, date) + '.txt') as fd:
        nrecords = sum(1 for record in csv.DictReader(fd))
        fd.seek(0)
        for job in csv.DictReader(fd, delimiter = '|'):
            if rerun: 
                pass
            elif Job.objects.filter(id = job['JobID']).exists(): 
                ctr += 1
                continue                
            json = {}
            json['id']         = job['JobID']
            json['project']    = job['Account']

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

            json['queue']      = job['Partition']
            json['name']       = job['JobName']
            json['status']     = job['State'].split()[0]

            json['nodes']      = int(job['NNodes'])
            json['cores']      = int(job['ReqCPUS'])
            json['wayness']     = json['cores']/json['nodes']

            json['date']       = json['end_time'].date()
            json['user']       = job['User']
            if json.has_key('user'):
                try: 
                    json['uid'] = int(pwd.getpwnam(json['user']).pw_uid)
                except: pass

            host_list = hostlist.expand_hostlist(job['NodeList'])
            del job['NodeList']

            Job.objects.filter(id=json['id']).delete()
            obj, created = Job.objects.update_or_create(**json)

            ### If xalt is available add data to the DB 
            xd = None
            try: xd = run.objects.using('xalt').filter(job_id = json['id'])[0]
            except: pass
            
            if xd:
                json['exe']     = xd.exec_path.split('/')[-1][0:128]
                json['exec_path'] = xd.exec_path
                json['cwd']     = xd.cwd[0:128]
                json['threads'] = xd.num_threads

                for join in join_run_object.objects.using('xalt').filter(run_id = xd.run_id):
                    object_path = lib.objects.using('xalt').get(obj_id = join.obj_id).object_path
                    module_name = lib.objects.using('xalt').get(obj_id = join.obj_id).module_name
                    if not module_name: module_name = 'none'
                    library = Libraries(object_path = object_path, module_name = module_name)
                    library.save()
                    library.jobs.add(obj)

            for host_name in host_list:
                h = Host(name=host_name)
                h.save()
                h.jobs.add(obj)

            ctr += 1
            progress(ctr, nrecords, date)


def update(date,rerun=False):

    tz = pytz.timezone('US/Central')
    pickle_dir = os.path.join(cfg.pickles_dir,date)

    ctr = 0
    for root, directory, pickle_files in os.walk(pickle_dir):
        num_files = len(pickle_files)
        print "Number of pickle files in",root,'=',num_files
        for pickle_file in sorted(pickle_files):

            ctr += 1
            try:
                if rerun: pass
                elif Job.objects.filter(id = pickle_file).exists(): 
                    continue                
            except:
                print pickle_file,"doesn't look like a pickled job"
                continue

            pickle_path = os.path.join(root,str(pickle_file))
            try:
                with open(pickle_path, 'rb') as f:
                    data = pickle.load(f)
                    json = data.acct
                    hosts = data.hosts.keys()
            except EOFError:
                print pickle_file, "is empty"
                continue

            if 'yesno' in json: del json['yesno']
            utc_start = datetime.utcfromtimestamp(
                json['start_time']).replace(tzinfo=pytz.utc)
            utc_end = datetime.utcfromtimestamp(
                json['end_time']).replace(tzinfo=pytz.utc)
            json['run_time'] = json['end_time'] - json['start_time']

            if json.has_key('unknown'):
                json['requested_time'] = json['unknown']*60
                del json['unknown']
            elif json.has_key('requested_time'): 
                json['requested_time'] = json['requested_time']*60
            else:
                json['requested_time'] = 0
            json['start_epoch'] = json['start_time']
            json['end_epoch'] = json['end_time']
            json['start_time'] = utc_start.astimezone(tz)
            json['end_time'] =  utc_end.astimezone(tz)
            json['date'] = json['end_time'].date()
            json['name'] = json['name'][0:128]
            json['wayness'] = json['cores']/json['nodes']
            if json.has_key('state'): 
                json['status'] = json['state']
                del json['state']
            json['status'] = json['status'].split()[0]
            try:
                if json.has_key('user'):
                    json['uid'] = int(pwd.getpwnam(json['user']).pw_uid)
                elif json.has_key('uid'):
                    json['user'] = pwd.getpwuid(int(json['uid']))[0]
            except: 
                json['user']='unknown'
                
            ### If xalt is available add data to the DB 
            xd = None
            try:
                xd = run.objects.using('xalt').filter(job_id = json['id'])[0]
                json['user']    = xd.user
                json['exe']     = xd.exec_path.split('/')[-1][0:128]
                json['exec_path'] = xd.exec_path
                json['cwd']     = xd.cwd[0:128]
                json['threads'] = xd.num_threads
            except: xd = False 
                
            if json.has_key('host_list'):
                del json['host_list']

            Job.objects.filter(id=json['id']).delete()
            obj, created = Job.objects.update_or_create(**json)
            for host_name in hosts:
                h = Host(name=host_name)
                h.save()
                h.jobs.add(obj)
                
            if xd:
                for join in join_run_object.objects.using('xalt').filter(run_id = xd.run_id):
                    try:
                        object_path = lib.objects.using('xalt').get(obj_id = join.obj_id).object_path
                        module_name = lib.objects.using('xalt').get(obj_id = join.obj_id).module_name
                        if not module_name: module_name = 'none'
                        library = Libraries(object_path = object_path, module_name = module_name)
                        library.save()
                        library.jobs.add(obj)
                    except: pass

            progress(ctr, num_files, date)

def update_metric_fields(date,rerun=False):
    update_comp_info()
    aud = exam.Auditor(processes=4)
    
    min_time = 600
    aud.stage(exam.GigEBW, ignore_qs=[], min_time = min_time)
    aud.stage(exam.HighCPI, ignore_qs=[], min_time = min_time)
    aud.stage(exam.HighCPLD, ignore_qs=[], min_time = min_time)
    aud.stage(exam.Load_L1Hits, ignore_qs=[], min_time = min_time)
    aud.stage(exam.Load_L2Hits, ignore_qs=[], min_time = min_time)
    aud.stage(exam.Load_LLCHits, ignore_qs=[], min_time = min_time)
    aud.stage(exam.MemBw, ignore_qs=[], min_time = min_time)
    aud.stage(exam.Catastrophe, ignore_qs=[], min_time = min_time)
    aud.stage(exam.MemUsage, ignore_qs=[], min_time = min_time)
    aud.stage(exam.PacketRate, ignore_qs=[], min_time = min_time)
    aud.stage(exam.PacketSize, ignore_qs=[], min_time = min_time)
    aud.stage(exam.Idle, ignore_qs=[], min_time = min_time)
    aud.stage(exam.LowFLOPS, ignore_qs=[], min_time = min_time)
    aud.stage(exam.VecPercent, ignore_qs=[], min_time = min_time)
    aud.stage(exam.CPU_Usage, ignore_qs = [], min_time = min_time)
    aud.stage(exam.MIC_Usage, ignore_qs = [], min_time = min_time)
    aud.stage(exam.Load_All, ignore_qs = [], min_time = min_time)
    aud.stage(exam.MetaDataRate, ignore_qs = [], min_time = min_time)
    aud.stage(exam.LnetAveMsgs, ignore_qs=[], min_time = min_time)
    aud.stage(exam.LnetAveBW, ignore_qs=[], min_time = min_time)
    aud.stage(exam.LnetMaxBW, ignore_qs=[], min_time = min_time)
    aud.stage(exam.InternodeIBAveBW, ignore_qs=[], min_time = min_time)
    aud.stage(exam.InternodeIBMaxBW, ignore_qs=[], min_time = min_time)
    aud.stage(exam.MDCReqs, ignore_qs=[], min_time = min_time)
    aud.stage(exam.MDCWait, ignore_qs=[], min_time = min_time)
    aud.stage(exam.OSCReqs, ignore_qs=[], min_time = min_time)
    aud.stage(exam.OSCWait, ignore_qs=[], min_time = min_time)
    aud.stage(exam.LLiteOpenClose, ignore_qs=[], min_time = min_time)

    print 'Run the following tests for:',date
    for name, test in aud.measures.iteritems():
        obj = TestInfo.objects.get(test_name = name)
        print obj.field_name,obj.threshold,obj.comparator

    jobs_list = Job.objects.filter(date = date).exclude(run_time__lt = min_time)

    # Use mem to see if job was tested.  It will always exist
    if not rerun:
        jobs_list = jobs_list.filter(OSCWait = None)
    
    paths = []
    for job in jobs_list:
        paths.append(os.path.join(cfg.pickles_dir,
                                  job.date.strftime('%Y-%m-%d'),
                                  str(job.id)))
        
    num_jobs = jobs_list.count()
    print '# Jobs to be tested:',num_jobs
    if num_jobs == 0 : return

    aud.run(paths)
    print 'finished computing metrics'

    for name, results in aud.metrics.iteritems():
        obj = TestInfo.objects.get(test_name = name)
        print name,len(results.keys())
        for jobid, result in results.iteritems():            
            try:
                jobs_list.filter(id = jobid).update(**{ obj.field_name : result })
            except:
                pass


if __name__ == "__main__":
    try:
        start = datetime.strptime(sys.argv[1],"%Y-%m-%d")
        try:
            end   = datetime.strptime(sys.argv[2],"%Y-%m-%d")
        except:
            end = start
    except:
        start = datetime.now()
        end   = datetime.now()

    for date in daterange(start, end):
        directory = date.strftime("%Y-%m-%d")
        update(directory, rerun = False)         
        update_metric_fields(directory, rerun = False)
