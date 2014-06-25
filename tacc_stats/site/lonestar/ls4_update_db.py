#!/usr/bin/env python
import os,sys
from datetime import timedelta,datetime
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
from tacc_stats.site.lonestar import views
from tacc_stats.pickler import MetaData as MetaData

path = "/hpc/tacc_stats_site/lonestar/pickles"
try:
    start = datetime.strptime(sys.argv[1],"%Y-%m-%d")
    end   = datetime.strptime(sys.argv[2],"%Y-%m-%d")
except:
    start = datetime.now() - timedelta(days=1)
    end   = start

for root,dirnames,filenames in os.walk(path):
    for directory in dirnames:

        date = datetime.strptime(directory,'%Y-%m-%d')
        if max(date.date(),start.date()) > min(date.date(),end.date()): continue
        print 'Run update for',date.date()

        meta = MetaData.MetaData(os.path.join(path,directory))
        meta.load_update()
        print 'Number of pickle files to upload into DB',len(meta.json.keys())
        views.update(meta = meta)

    break
