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
    end   = datetime.strptime(sys.argv[2],"%Y-%m-%d")
except:
    start = datetime.now() - timedelta(days=1)
    end   = start

for root,dirnames,filenames in os.walk(cfg.pickles_dir):
    for directory in dirnames:
        try:
            date = datetime.strptime(directory,'%Y-%m-%d')
            if max(date.date(),start.date()) > min(date.date(),end.date()): continue
            print 'Run update for',date.date()
        except: continue

        views.update(directory,rerun=False)        
        views.update_metric_fields(directory,rerun=False)
        
    break
