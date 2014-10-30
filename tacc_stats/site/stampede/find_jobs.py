#!/usr/bin/env python
import os
try:
    import django
    django.setup()
except:
    os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView
from django.db.models import Q
from tacc_stats.site.stampede.models import Job, JobForm
    
    
fields = {'date__gte' : '2014-10-20', 'run_time__gte' : '3600'}

jobs_list = Job.objects.filter(**fields)
for job in jobs_list:
    print job.id

