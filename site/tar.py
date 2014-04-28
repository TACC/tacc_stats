#!/usr/bin/env python

import os,sys 
from subprocess import Popen, PIPE
import datetime

tar_dir = '/hpc/tacc_stats/stampede/pickles/'
untar_dir = '/hpc/tacc_stats_site/stampede/pickles/'

p = Popen(["date --date " + sys.argv[1] + ' +%Y-%m-%d'], stdout = PIPE, 
                   shell = True) 
date_start = p.communicate()[0].strip()

p = Popen(["date --date " + sys.argv[2] + ' +%Y-%m-%d'], stdout = PIPE,
                   shell = True) 
date_end = p.communicate()[0].strip()

s = [int(x) for x in date_start.split('-')]
e = [int(x) for x in date_end.split('-')]

for tarball in os.listdir(tar_dir):
    date = tarball.split('.')[0]
    d = [int(x) for x in date.split('-')]

    if not datetime.date(s[0],s[1],s[2]) <= datetime.date(d[0],d[1],d[2]) <= datetime.date(e[0],e[1],e[2]): continue

    tar_path = str(os.path.join(tar_dir,tarball))
    print tar_path
    p = Popen(["/bin/tar -zxvf " + tar_path + " -C " + untar_dir],shell=True)
    p.communicate()

