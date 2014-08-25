#!/usr/bin/env python
import os,sys
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView
from django.db.models import Q
from tacc_stats.site.stampede.models import Job, JobForm
    
    
def search(kwargs):
    print "{0:10}  {1:20}  {2:10}  {3}".format('id', 'exe', 'user', 'sus')
    for f in kwargs:
        job = Job.objects.get(id=f)

        print "{0:10}  {1:20}  {2:10}  {3:0.2f}".format(job.id,job.exe,job.user,job.nodes*16*job.run_time/3600.)

file_list = list(open(sys.argv[1],'r'))
search(file_list)
