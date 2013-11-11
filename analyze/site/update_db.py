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
views.update()
