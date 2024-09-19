#!/usr/bin/env python
import os,sys, pwd
sys.path.append("/home/sg99/tacc_stats")
from datetime import timedelta, datetime
import psycopg2

os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
import django
django.setup()

from tacc_stats.site.machine.models import job_data, metrics_data
from tacc_stats.analysis.metrics import metrics

import conf_parser as cfg
from tacc_stats.progress import progress

CONNECTION = cfg.get_db_connection_string()

query_create_metric_table = """CREATE TABLE IF NOT EXISTS metrics_data (
                                           id     SERIAL PRIMARY KEY,
                                           jid    VARCHAR(32),
                                           type   VARCHAR(32),
                                           metric VARCHAR(32),
                                           units  VARCHAR(16),                                            
                                           value  real,                                           
                                           FOREIGN KEY(jid) REFERENCES job_data(jid),
                                           UNIQUE (jid, type, metric)
                                           );"""
query_create_jobindex = "CREATE INDEX ON metrics_data (jid);"


def create_metrics_table(reset = False):
    conn = psycopg2.connect(CONNECTION)
    with conn.cursor() as cur:
        if reset:
            cur.execute("DROP TABLE IF EXISTS metrics_data CASCADE;")
        cur.execute(query_create_metric_table)
        cur.execute(query_create_jobindex)
    conn.commit()    
    conn.close()


def update_metrics(date, rerun = False):

    min_time = 300
    jobs_list = list(job_data.objects.filter(end_time__date = date.date()).exclude(runtime__lt = min_time))
    print("Total jobs {0}".format(len(jobs_list)) + " for date " + date.strftime("%Y-%m-%d"))

    if not rerun:
        jobs_list = [job for job in jobs_list if not job.metrics_data_set.all().exists() or job.metrics_data_set.all().filter(value__isnull = True).count() > 0]

    # Set up metric computation manager
    metrics_manager = metrics.Metrics(processes = 2)

    print("Compute for following metrics for date {0} on {1} jobs".format(date, len(jobs_list)))
    for name in metrics_manager.metrics_list:
        print(name)        
    
    metrics_manager.run(jobs_list)


if __name__ == "__main__":

    #################################################################
    try:
        startdate = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except: 
        startdate = datetime.combine(datetime.today(), datetime.min.time())
    try:
        enddate   = datetime.strptime(sys.argv[2], "%Y-%m-%d")
    except:
        enddate = startdate

    print("###Date Range of metrics to update: {0} -> {1}####".format(startdate, enddate))
    #################################################################

    create_metrics_table(reset = False)

    date = startdate
    while date <= enddate:
        update_metrics(date, rerun = False)
        date += timedelta(days=1)
