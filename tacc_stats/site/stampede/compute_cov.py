#!/usr/bin/env python
import os,sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "tacc_stats.site.tacc_stats_site.settings")
import django
django.setup()

from django.db.models import Q
from tacc_stats.site.stampede.models import Job
    
from numpy import corrcoef
    
first = sys.argv[1]
second = sys.argv[2]

fields = {'date' : '2014-10-30', 'run_time__gte' : '3600', first+'__isnull' : False, second+'__isnull' : False}

jobs_list = Job.objects.filter(**fields)

print first,second
print corrcoef(jobs_list.values_list(first,flat=True), 
               jobs_list.values_list(second,flat=True))

#for job in jobs_list:
#    print job.cpld

