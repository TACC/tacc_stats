#!/usr/bin/env python3
import os,sys,time
from datetime import timedelta, datetime

import psycopg2
from pgcopy import CopyManager

from pandas import read_sql, read_csv, to_datetime, to_timedelta, concat
import hostlist

CONNECTION = "dbname=ls6_db1 user=postgres port=5432"

query_create_jobdata_table = """CREATE TABLE IF NOT EXISTS job_data (
jid         VARCHAR(32) NOT NULL,
submit_time TIMESTAMPTZ NOT NULL,
start_time  TIMESTAMPTZ NOT NULL,
end_time    TIMESTAMPTZ NOT NULL,
runtime     REAL,
timelimit   REAL, 
node_hrs    REAL, 
nhosts      INT CHECK (nhosts > 0), 
ncores      INT CHECK (ncores > 0),
username    VARCHAR(64) NOT NULL,
account     VARCHAR(64),
queue       VARCHAR(64),
state       VARCHAR(64),
jobname     TEXT,
host_list   TEXT[],
CHECK (start_time <= end_time),
CHECK (submit_time <= start_time),
CHECK (runtime >= 0),
CHECK (timelimit >= 0),
CHECK (node_hrs >= 0),
UNIQUE(jid)
);"""

query_create_jobindex = "CREATE INDEX ON job_data (jid);"

conn = psycopg2.connect(CONNECTION)
print(conn.server_version)

"""
with conn.cursor() as cur:
    #cur.execute("DROP TABLE IF EXISTS job_data;")
    cur.execute(query_create_jobdata_table)
    cur.execute(query_create_jobindex)
    conn.commit()
conn.close()
"""
def sync_acct(acct_file, date_str):
    print(date_str)
    conn = psycopg2.connect(CONNECTION)
    edf = read_sql("select jid from job_data where date(end_time) = '{0}' ".format(date_str), conn)

    df = read_csv(acct_file, sep='|')
    df.rename(columns = {'JobID': 'jid', 'User': 'username', 'Account' : 'account', 'Start' : 'start_time', 
                         'End' : 'end_time', 'Submit' : 'submit_time', 'Partition' : 'queue', 
                         'Timelimit' : 'timelimit', 'JobName' : 'jobname', 'State' : 'state', 
                         'NNodes' : 'nhosts', 'ReqCPUS' : 'ncores', 'NodeList' : 'host_list'}, inplace = True)
    df["jid"] = df["jid"].apply(str)

    df["start_time"] = to_datetime(df["start_time"]).dt.tz_localize('US/Central')
    df["end_time"] = to_datetime(df["end_time"]).dt.tz_localize('US/Central')
    df["submit_time"] = to_datetime(df["submit_time"]).dt.tz_localize('US/Central')

    df["runtime"] = to_timedelta(df["end_time"] - df["start_time"]).dt.total_seconds()    
    df["timelimit"] = df["timelimit"].str.replace('-', ' days ')
    df["timelimit"] = to_timedelta(df["timelimit"]).dt.total_seconds()
                         
    df["host_list"] = df["host_list"].apply(hostlist.expand_hostlist)
    df["node_hrs"] = df["nhosts"]*df["runtime"]/3600.

    df = df[~df["jid"].isin(edf["jid"])]

    mgr = CopyManager(conn, 'job_data', df.columns)
    mgr.copy(df.values.tolist())
    conn.commit()
    conn.close()
    


"""
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
"""
"""
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
        "avg_oscwait", "avg_openclose", "avg_mcdrambw", "avg_blockbw", "max_load15", "avg_gpuutil"
    ]

    aud = metrics.Metrics(metric_names, processes = processes)

    print("Run the following tests for:",date)
    for name in aud.metric_list:
        print(name)

    jobs_list = Job.objects.filter(date = date).exclude(run_time__lt = min_time)
    #jobs_list = Job.objects.filter(date = date, queue__in = ['rtx', 'rtx-dev']).exclude(run_time__lt = min_time)

    # Use avg_cpuusage to see if job was tested.  It will always exist
    if not rerun:
        jobs_list = jobs_list.filter(avg_cpuusage = None)

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
"""
if __name__ == "__main__":

    while True:

        #################################################################
        try:
            startdate = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        except:
         startdate = datetime.combine(datetime.today(), datetime.min.time())
        try:
            enddate   = datetime.strptime(sys.argv[2], "%Y-%m-%d")
        except:
            enddate = startdate + timedelta(days = 1)

        print("###Date Range of job files to ingest: {0} -> {1}####".format(startdate, enddate))
        #################################################################

        # Parse and convert raw stats files to pandas dataframe
        start = time.time()
        directory = "/tacc_stats_site/ls6/accounting"
        
        while startdate <= enddate:            
            for entry in os.scandir(directory):
                if not entry.is_file(): continue
                if entry.name.startswith(str(startdate.date())):
                    sync_acct(entry.path, str(startdate.date()))
            startdate += timedelta(days=1)
        print("loading time", time.time() - start)

        time.sleep(900)
