#!/usr/bin/env python
from django.core.management import setup_environ
import os,sys,fnmatch,re,json
from subprocess import Popen, PIPE

cwd = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cwd,'../lib'))


from tacc_stats_site import settings
setup_environ(settings)
from stampede import views
import sys_conf
import datetime
from analysis.gen import tspl, lariat_utils

path = sys_conf.pickles_dir

p = Popen(["date --date " + sys.argv[1] + ' +%Y-%m-%d'], stdout = PIPE, 
                   shell = True) 
date_start = p.communicate()[0].strip()

p = Popen(["date --date " + sys.argv[2] + ' +%Y-%m-%d'], stdout = PIPE,
                   shell = True) 
date_end = p.communicate()[0].strip()


job_mpi_data = {}
for date in os.listdir(path):
    
    s = [int(x) for x in date_start.split('-')]
    e = [int(x) for x in date_end.split('-')]
    d = [int(x) for x in date.split('-')]

    if not datetime.date(s[0],s[1],s[2]) <= datetime.date(d[0],d[1],d[2]) <= datetime.date(e[0],e[1],e[2]): continue
    
    print 'Run update for',date


    directory = sys_conf.lariat_path
    matches=[]
    for root, dirnames, filenames in os.walk(directory):
        for fn in fnmatch.filter(filenames,'*'+date+'.json'):
            matches.append(os.path.join(root,fn))

    ld = {}
    if len(matches) != 0:
        for m in matches:
            print 'Load lariat data for date',date,'from',m

            try:
                ld.update(json.load(open(m))) # Should be only one match
            except:
                json_str = open(m).read()
                json_str = re.sub(r'\\','',json_str)
                ld.update(json.loads(json_str))


    for job,data in ld.iteritems():
        try:
            keys = ' '.join(data[0]['pkgT'].keys())
            nodes = data[0]['numNodes']
            for lib in data[0]['pkgT'].keys():
                if 'mvapich' in lib or 'impi' in lib: 
                    job_mpi_data[job]=(nodes,lib)
        except: 
            pass

import cPickle as pickle
f = open('mpi_data-'+date_start+'.'+date_end,'wb')
pickle.dump(job_mpi_data,f)
