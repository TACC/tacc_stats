#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "tacc_stats.site.tacc_stats_site.settings")
import django
django.setup()

from django.db.models import Q,Sum
from tacc_stats.site.stampede.models import Job
from tacc_stats.site.xalt.models import run
from tacc_stats.analysis.gen import lariat_utils
import tacc_stats.cfg as cfg
 
ld = lariat_utils.LariatData(directory = cfg.lariat_path,
                             daysback = 2)

acct_jobs_list = Job.objects.filter(date__range = ["2013-10-01", "2013-10-31"]).exclude(exe = "unknown").exclude(status = "FAILED")
runs_list = run.objects.using('xalt').exclude(job_id = "unknown")

ctr = 0
app_dict = {}
for job in acct_jobs_list:
    exec_list = []

    factor = 16*0.0002777777777777778
    if job.queue == "largemem": factor *= 2

    sus = 0
    if runs_list.filter(job_id = job.id).exists():
        runs = runs_list.filter(job_id = job.id)
        for run in runs: 
            sus += run.run_time*run.num_nodes*factor
            exe = run.exec_path.split('/')[-1]
            app_dict.setdefault(exe, 0.0)
            app_dict[exe] += sus
            exec_list.append(exe)
    else:
        exec_list = []
        ld.set_job(str(job.id), end_time = job.date.strftime("%Y-%m-%d"))
        for run in ld.ld_json[str(job.id)]:
            sus += int(float(run['runTime']))*int(run['numNodes'])*factor
            exe = run['exec'].split('/')[-1]
            app_dict.setdefault(exe, 0.0) 
            app_dict[exe] += sus
            exec_list.append(exe)

    print job.id, job.nodes,job.threads,job.sus(),
    print ' '.join(exec_list)

import operator
sorted_apps = sorted(app_dict.items(), key = operator.itemgetter(1))[::-1]

for app in sorted_apps[0:20]:
    print app
