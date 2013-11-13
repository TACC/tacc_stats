#!/usr/bin/env python
from django.core.management import setup_environ
import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'tacc_stats_site'))
sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'stats'))
import settings
setup_environ(settings)

import views
import MetaData
import sys_path_append

path = sys_path_append.pickles_dir

for date in os.listdir(path):
    print 'Date',date

    meta = MetaData.MetaData(os.path.join(path,date))
    if os.path.exists(meta.meta_path):continue
    meta.load_update()

    views.update(meta = meta)

