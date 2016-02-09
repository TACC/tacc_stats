#!/usr/bin/env python
import os,sys
from datetime import timedelta,datetime
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
import django
django.setup()

from tacc_stats.site.machine import views
import tacc_stats.cfg as cfg

try:
    start = datetime.strptime(sys.argv[1],"%Y-%m-%d")
    try:
        end   = datetime.strptime(sys.argv[2],"%Y-%m-%d")
    except:
        end = start
except:
    start = datetime.now()
    end   = datetime.now()

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

for date in daterange(start, end):
    directory = date.strftime("%Y-%m-%d")
    views.update(directory, rerun = False)         
    views.update_metric_fields(directory, rerun = True)
