#!/usr/bin/env python
import os,sys, pwd
from datetime import timedelta, datetime
from dateutil.parser import parse
from fcntl import flock, LOCK_EX, LOCK_NB
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
import django
django.setup()
from tacc_stats.site.machine.models import job_data
from tacc_stats.analysis.metrics import metrics
import tacc_stats.cfg as cfg
from tacc_stats.progress import progress
from tacc_stats.daterange import daterange
import traceback


def update_metrics(date, processes, rerun = False):

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
    
    jobs_list = job_data.objects.filter(end_time__date = date.date()).exclude(runtime__lt = min_time)

    # Count jobs that meet metric criteria
    num_jobs = jobs_list.count()
    print("# Jobs that can be tested:",num_jobs)
    if num_jobs == 0 : return

    # Count jobs that have not been measured or recompute metrics
    # Use avg_cpuusage to see if job was tested.  It will always exist
    #if not rerun:
    #    jobs_list = jobs_list.filter(avg_cpuusage = None)

    num_jobs = jobs_list.count()
    print("# Jobs that have not been tested:",num_jobs)
    if num_jobs == 0 : return

    # Set up metric computation manager
    aud = metrics.Metrics(metric_names, processes = processes)
    print("Run the following tests for:",date)
    for name in aud.metric_list:
        print(name)

    for x in aud.run(jobs_list):
        print(x)
    sys.exit()
    for jobid, metric_dict in aud.run(jobs_list):
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

    args = parser.parse_args()    
    start = args.start
    end   = args.end
    if not end: end = start

    for date in daterange(start, end):
        update_metrics(date, args.processes, rerun = False)
