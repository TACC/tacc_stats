#!/usr/bin/env python
import os,sys
os.environ['DJANGO_SETTINGS_MODULE']='site.settings'
import django
django.setup()
from tacc_stats.site.machine import views

t = open(sys.argv[1]).readlines()

thresholds = {}
for line in t:
    key,op,val = line.split()
    thresholds[key] = [op,val]

views.update_comp_info(thresholds)


