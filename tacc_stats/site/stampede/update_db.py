#!/usr/bin/env python
import os,sys
from datetime import timedelta,datetime
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
from tacc_stats.site.stampede import views
import tacc_stats.cfg as cfg
import tacc_stats.analysis.exam as exam

try:
    start = datetime.strptime(sys.argv[1],"%Y-%m-%d")
    end   = datetime.strptime(sys.argv[2],"%Y-%m-%d")
except:
    start = datetime.now() - timedelta(days=1)
    end   = start

for root,dirnames,filenames in os.walk(cfg.pickles_dir):
    for directory in dirnames:

        date = datetime.strptime(directory,'%Y-%m-%d')
        if max(date.date(),start.date()) > min(date.date(),end.date()): continue
        print 'Run update for',date.date()

        #views.update(directory,rerun=False)        

        aud = exam.Auditor(processes=1)
        
        aud.stage(exam.HighCPI,threshold=1.0,ignore_status=['FAILED,CANCELLED'])
        aud.stage(exam.MemBw,threshold=0.5,ignore_status=['FAILED,CANCELLED'])
        aud.stage(exam.Catastrophe,threshold=0.001)
        aud.stage(exam.MemUsage,threshold=30)
        aud.stage(exam.PacketRate,threshold=1e6,ignore_status=['FAILED,CANCELLED'])
        aud.stage(exam.PacketSize,threshold=64,ignore_status=['FAILED,CANCELLED'])
        aud.stage(exam.Idle,threshold=0.999,min_hosts=2,
                  ignore_status=['FAILED,CANCELLED'])        

        views.update_test_field(directory,aud)
        
    break
