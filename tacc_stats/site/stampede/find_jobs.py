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
    strfmt = '{0:10} {1:10} {2:10} {3:20} {4:10} {5:20}'
    print strfmt.format('id', 'date','user','exe', 'sus',kwargs)
    for job in jobs_list:
        
        print strfmt.format(str(job.id),str(job.date),str(job.user),str(job.exe),'{0:.2f}'.format(16*job.run_time/3600.*job.nodes),'{0:.2f}'.format(job.packetrate))+'{0:.2f}'.format(job.packetsize)

    """
        if job.user in data:
            data[job.user] += job.run_time/3600.*job.nodes*16
        else:
            data[job.user] = job.run_time/3600.*job.nodes*16

    print '-------------------------'
    for x,v in data.iteritems():
        print x,v
    """

fields = {'date__gte' : '2014-10-12'}#, 
#          'packetsize__lte' : 64*2**10}


search(fields)
