#!/usr/bin/env python
import os
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView
from django.db.models import Q
from tacc_stats.site.stampede.models import Job, JobForm
    
    
def search(kwargs):
    jobs_list = Job.objects.filter(**kwargs)

    data = {}
    for job in jobs_list:
        print job.user,job.run_time/3600.*job.nodes
        if job.user in data:

            data[job.user] += job.run_time/3600.*job.nodes*16
        else:
            data[job.user] = job.run_time/3600.*job.nodes*16
    print '-------------------------'
    for x,v in data.iteritems():
        print x,v


fields = {'exe__icontains' : 'release'}


search(fields)
