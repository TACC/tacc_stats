#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "tacc_stats.site.tacc_stats_site.settings")
import django
django.setup()

from django.db.models import Q
from tacc_stats.site.stampede.models import Job
    
    
fields = {'date__gte' : '2014-10-20', 'run_time__gte' : '3600'}

jobs_list = Job.objects.filter(**fields)
for job in jobs_list:
    print job.id

