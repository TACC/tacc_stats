#!/usr/bin/env python
import os,sys
from subprocess import Popen, PIPE, call

import datetime
import high_cpi_or_cpe
path = sys.argv[1]

p = Popen(["date --date " + sys.argv[2] + ' +%Y-%m-%d'], stdout = PIPE, 
                   shell = True) 
date_start = p.communicate()[0].strip()

p = Popen(["date --date " + sys.argv[3] + ' +%Y-%m-%d'], stdout = PIPE,
                   shell = True) 
date_end = p.communicate()[0].strip()

for date in os.listdir(path):
    try:
        s = [int(x) for x in date_start.split('-')]
        e = [int(x) for x in date_end.split('-')]
        d = [int(x) for x in date.split('-')]
    except: continue
    if not datetime.date(s[0],s[1],s[2]) <= datetime.date(d[0],d[1],d[2]) <= datetime.date(e[0],e[1],e[2]): continue
    
    print 'Run CPI analysis for',date
    files = os.path.join(path,date)
    call(["./high_cpi_or_cpe.py -p 4 -o v1high_cpi_" + date + ".txt " + files], 
         shell = True)

