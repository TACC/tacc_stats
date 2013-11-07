#!/usr/bin/env python
from django.core.management import setup_environ
import sys
sys.path.append('./tacc_stats_site')
sys.path.append('./stats')
import settings
setup_environ(settings)
import views
views.update()
