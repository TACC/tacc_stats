#!/usr/bin/env python
from django.core.management import setup_environ
import os,sys,subprocess
sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'tacc_stats_site'))
sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'lonestar'))
import settings
setup_environ(settings)

import lonestar.views as views
import lonestar.sys_path_append as sys_path_append
import MetaData


path = sys_path_append.pickles_dir
date_str = sys.argv[1] 

for date in os.listdir(path):
    
    date_str = subprocess.check_output(['date', '--date', date_str, '+%Y-%m-%d'])
    #if date.strip() != date_str.strip(): continue
    print 'Run update for',date
    meta = MetaData.MetaData(os.path.join(path,date))
    #if os.path.exists(meta.meta_path): continue
    meta.load_update()
    print 'Number of pickle files to upload into DB',len(meta.json.keys())
    views.ls4_update(meta = meta)

