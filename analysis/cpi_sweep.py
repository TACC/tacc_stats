#!/usr/bin/env python
import os,sys
from subprocess import Popen, PIPE, call

import datetime
sys.path.append(os.path.join(os.path.dirname(__file__),
                             '../lib'))
import analysis.exam.tests as tests
import analysis.gen.tspl_utils as tspl_utils
import sys_conf

path = sys_conf.pickles_dir
p = Popen(["date --date " + sys.argv[1] + ' +%Y-%m-%d'], stdout = PIPE, 
                   shell = True) 
date_start = p.communicate()[0].strip()

p = Popen(["date --date " + sys.argv[2] + ' +%Y-%m-%d'], stdout = PIPE,
                   shell = True) 
date_end = p.communicate()[0].strip()

cpi_test = tests.HighCPI(processes=2, threshold=1.0)

for date in os.listdir(path):
    try:
        s = [int(x) for x in date_start.split('-')]
        e = [int(x) for x in date_end.split('-')]
        d = [int(x) for x in date.split('-')]
    except: continue
    if not datetime.date(s[0],s[1],s[2]) <= datetime.date(d[0],d[1],d[2]) <= datetime.date(e[0],e[1],e[2]): 
        continue
    
    print 'Run CPI analysis for',date
    files = os.path.join(path,date)
    filelist=tspl_utils.getfilelist(files)

    cpi_test.run(filelist)

    print date
    print cpi_test.failed()

