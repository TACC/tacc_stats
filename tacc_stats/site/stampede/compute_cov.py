#!/usr/bin/env python
import os,sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "tacc_stats.site.tacc_stats_site.settings")
import django
django.setup()

from django.db.models import Q
from tacc_stats.site.stampede.models import Job
    
from numpy import corrcoef
    
date_start = sys.argv[1]
date_stop = sys.argv[2]

first = sys.argv[3]
second = sys.argv[4]

fields = {'date__range' : (date_start, date_stop), 'run_time__gte' : '3600', first+'__isnull' : False, second+'__isnull' : False}

jobs_list = Job.objects.filter(**fields)#.exclude(**{first : float('nan')}).exclude(**{second : float('nan')})

print first,second
print corrcoef(jobs_list.values_list(first,flat=True), 
               jobs_list.values_list(second,flat=True))

#for job in jobs_list:
#    print job.cpld

