#!/usr/bin/env python3
import os,sys,time
from datetime import timedelta, datetime

import psycopg2
from pgcopy import CopyManager

from pandas import read_csv, to_datetime, to_timedelta, concat

import hostlist

from tacc_stats.analysis.gen.utils import read_sql
from tacc_stats import cfg

CONNECTION = "dbname={0} user=postgres port=5432".format(cfg.dbname)

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

with conn.cursor() as cur:
    #cur.execute("DROP TABLE IF EXISTS job_data;")
    cur.execute(query_create_jobdata_table)
    cur.execute(query_create_jobindex)
    conn.commit()
conn.close()

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
    
if __name__ == "__main__":

#    while True:

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
        directory = cfg.acct_path
        
        while startdate <= enddate:            
            for entry in os.scandir(directory):
                if not entry.is_file(): continue
                if entry.name.startswith(str(startdate.date())):
                    print(entry.path)
                    sync_acct(entry.path, str(startdate.date()))
            startdate += timedelta(days=1)
        print("loading time", time.time() - start)

        #time.sleep(900)
