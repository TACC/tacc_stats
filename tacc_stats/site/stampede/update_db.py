#!/usr/bin/env python
import os,sys
from datetime import date
from subprocess import Popen, PIPE
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
from tacc_stats.site.stampede import views
import tacc_stats.cfg as cfg
import tacc_stats.analysis as analysis

def get_date(arg):
    p = Popen(["date --date " + arg + ' +%Y-%m-%d'], stdout = PIPE, 
              shell = True) 
    return p.communicate()[0].strip()

date_start = get_date(sys.argv[1])
date_end   = get_date(sys.argv[2])

for date_dir in os.listdir(cfg.pickles_dir):
    
    s = [int(x) for x in date_start.split('-')]
    e = [int(x) for x in date_end.split('-')]
    d = [int(x) for x in date_dir.split('-')]

    if not date(s[0],s[1],s[2]) <= date(d[0],d[1],d[2]) <= date(e[0],e[1],e[2]): continue
    
    print 'Run update for',date_dir

    #views.update(date_dir)

    cpi_test = analysis.HighCPI(threshold=1.0,processes=2)
    views.update_test_field(date_dir,cpi_test,'cpi',rerun=True)

    mbw_test = analysis.MemBw(threshold=0.5,processes=1)               
    views.update_test_field(date_dir,mbw_test,'mbw')   

    idle_test = analysis.Idle(threshold=0.999,processes=1,min_hosts=2)
    views.update_test_field(date_dir,idle_test,'idle',rerun=True)   

    cat_test = analysis.Catastrophe(threshold=0.001,processes=1,min_hosts=2)
    views.update_test_field(date_dir,cat_test,'cat')   
