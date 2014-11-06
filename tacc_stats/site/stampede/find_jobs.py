#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "tacc_stats.site.tacc_stats_site.settings")
import django
django.setup()

from django.db.models import Q,Sum
from tacc_stats.site.stampede.models import Job
from tacc_stats.site.xalt.models import run
    
jobs_list = Job.objects.filter(date__range=["2014-10-01","2014-10-31"])
noibrun_list = jobs_list.filter(exe='unknown')

print 'Total Jobs',jobs_list.count()
print '% Jobs using ibrun', (1-float(noibrun_list.count())/jobs_list.count())*100.

noibrun_sus = 0
for job in noibrun_list:
    noibrun_sus += job.run_time*job.nodes

sus = 0
for job in jobs_list:
    sus += job.run_time*job.nodes

print 'Total SUs',16*sus/3600.
print '% SUs using ibrun',(1-float(noibrun_sus)/sus)*100


runs_list = run.objects.using('xalt').filter(date__range=["2014-10-01","2014-10-31"])

sus = 0
for run in runs_list:
    
    sus += 16*run.run_time*run.num_nodes
print 'XALT SUs',sus/3600.

