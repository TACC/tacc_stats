#!/usr/bin/env python
from django.core.management import setup_environ
import os,sys
from subprocess import Popen, PIPE

sys.path.append(os.path.join(os.path.dirname(__file__), 
                             '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'tacc_stats_site'))
sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'stampede'))
import settings
setup_environ(settings)

import stampede.views as views
import sys_conf
import datetime

path = sys_conf.pickles_dir

p = Popen(["date --date " + sys.argv[1] + ' +%Y-%m-%d'], stdout = PIPE, 
                   shell = True) 
date_start = p.communicate()[0].strip()

p = Popen(["date --date " + sys.argv[2] + ' +%Y-%m-%d'], stdout = PIPE,
                   shell = True) 
date_end = p.communicate()[0].strip()

for date in os.listdir(path):
    
    s = [int(x) for x in date_start.split('-')]
    e = [int(x) for x in date_end.split('-')]
    d = [int(x) for x in date.split('-')]

    if not datetime.date(s[0],s[1],s[2]) <= datetime.date(d[0],d[1],d[2]) <= datetime.date(e[0],e[1],e[2]): continue
    
    print 'Run update for',date
    views.update(date)
