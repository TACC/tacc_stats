#!/usr/bin/env python
import os, sys 
from influxdb import InfluxDBClient
from datetime import datetime, timedelta
import gzip
from dateutil.parser import parse
from multiprocessing import Pool

client = InfluxDBClient(database='ls5_jobs_db')
rootdir = "/hpc/tacc_stats_site/ls5/archive"
acctdir = "/hpc/tacc_stats_site/ls5/accounting"
#client.drop_database('ls5_jobs_db')
client.create_database('ls5_jobs_db')

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def create_job_map(start_date, end_date):
    job_map = {}
    for single_date in daterange(start_date, end_date):
        file_name = os.path.join(acctdir, single_date.strftime("%Y-%m-%d")) + ".txt"
        print file_name
        with open(file_name, 'r') as fd:
            for line in fd.readlines():
                job,user,rest = line.split('|',2)
                job_map[job] = user
    return job_map

if len(sys.argv) == 1:
    end_date = datetime.now()
    start_date = datetime.now() - timedelta(hours = 1)
elif len(sys.argv) == 3:
    end_date = parse(sys.argv[1])
    start_date = parse(sys.argv[2])

job_map = create_job_map(start_date, end_date)
def input_data(dirname):

    first_time = start_date.strftime('%s')
    last_time = end_date.strftime('%s')

    prev = {}
    result = client.query("select reqs from mdc where host = '{0}'".format(dirname), epoch = True)

    if result: times = sorted(list(set([t['time'] for t in list(result)[0]])))
    else: times = []
    file_list = sorted(os.listdir(os.path.join(rootdir, dirname))) 
    json = []

    for f in file_list:        
        if not f[0].isdigit(): continue

        first_file_time = int(f.split('.')[0])
        last_file_time = int(f.split('.')[0]) + 86400

        if last_file_time < int(first_time): continue
        if first_file_time > int(last_time): continue

        print dirname, f        
        try: 
            f.split('.')[1] == "gz" 
            open_method = gzip.open
        except: open_method = open

        with open_method(os.path.join(rootdir, dirname, f), 'r') as fd:
            schema = {}

            for line in fd:
                if line[0] == '!':
                    typename, events = line.split(' ',1)
                    schema[typename[1:]] = events.split()
                if line[0].isdigit(): 
                    timestamp, jobid, hostname = line.split()
                    timestamp =  int(float(timestamp)*1e6)*1000
                    #if timestamp == times[-1]: continue
                    #print timestamp,times
                    while True:
                        try: 
                            line = fd.next()
                        except: break
                            
                        if line[0].isalpha(): pass
                        elif line[0] == '%': continue
                        else: break

                        typename, device, values = line.split(' ',2)
                        if typename not in ['mdc', 'osc', 'llite', 'cpu', 'lnet']: continue
                        """
                        if job_map.has_key(jobid): 
                            username = job_map[jobid]
                        else: 
                            username = ''
                        """

                        sample = {"measurement" : typename,
                                  "time" : timestamp,   
                                  "tags" : {"device" : device, "jobid" : jobid},
                                  "fields" : {"host" : hostname}
                        }
                            
                        for idx, value in enumerate(values.split()):
                            value = float(value)
                            eventname, eventinfo = schema[typename][idx].split(',',1)
                            key = typename + ' ' + device + ' ' + eventname
                            if not key in prev:
                                prev[key] = value
                                continue
                            if eventinfo: sample["fields"][eventname + "_info"] = "\"" + eventinfo + "\"" 
                            if value >= prev[key]: 
                                sample["fields"][eventname] = value - prev[key]
                            else: sample["fields"][eventname] = value
                            prev[key] = value
                        
                        if timestamp not in times and sample["fields"]:
                            json += [sample]

    try:
        if json:            
            print len(json)
            client.write_points(json, batch_size = 1000)            
            print 'write points for host',dirname
    except: 
        print "write failed for host",dirname


p = Pool(4)
p.map(input_data, os.listdir(rootdir))
