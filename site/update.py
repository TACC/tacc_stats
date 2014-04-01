#!/usr/bin/env python
from django.core.management import setup_environ
import os,sys
from subprocess import Popen, PIPE

sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'tacc_stats_site'))
sys.path.append(os.path.join(os.path.dirname(__file__), 
                             'stampede'))
import settings
setup_environ(settings)

import stampede.views as views
views.update(sys.argv[1])
