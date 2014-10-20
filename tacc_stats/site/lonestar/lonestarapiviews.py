from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView

from tacc_stats.site.lonestar.models import LS4Job, LS4JobForm
import os,sys

from tacc_stats.analysis.gen import tspl, lariat_utils
import tacc_stats.analysis.plot as plot

from tacc_stats.pickler import job_stats, batch_acct
sys.modules['pickler.job_stats'] = job_stats
sys.modules['pickler.batch_acct'] = batch_acct
sys.modules['job_stats'] = job_stats
sys.modules['batch_acct'] = batch_acct
import cPickle as pickle 
import time
   
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from django.core.cache import cache,get_cache
import base64
import json
from cStringIO import StringIO

def figure_to_base64(p):
    sio = StringIO()
    p.fig.savefig(sio, format='png')
    return base64.standard_b64encode(sio.getvalue())

def get_data(pk):
    if cache.has_key(pk):
        data = cache.get(pk)
    else:
        job = LS4Job.objects.get(pk = pk)
        with open(job.path,'rb') as f:
            data = pickle.load(f)
            cache.set(job.id, data)
    return data

def master_plot(request, pk):
    data = get_data(pk)
    mp = plot.MasterPlot(lariat_data="pass")
    mp.plot(pk,job_data=data)
    return figure_to_base64(mp)

def heat_map(request, pk):
    
    data = get_data(pk)
    hm = plot.HeatMap({'intel' : ['intel_pmc3','intel_pmc3']},
                          {'intel' : ['CLOCKS_UNHALTED_REF',
                                      'INSTRUCTIONS_RETIRED']},
                          lariat_data="pass")
    hm.plot(pk,job_data=data)
    return figure_to_base64(hm)

def build_schema(data,name):
    schema = []
    for key,value in data.get_schema(name).iteritems():
        if value.unit:
            schema.append(value.key + ','+value.unit)
        else: schema.append(value.key)
    return schema

def type_list(job_id):
    data = get_data(job_id)
    type_list = []
    host0=data.hosts.values()[0]
    for type_name, type in host0.stats.iteritems():
        schema = ' '.join(build_schema(data,type_name))
        type_list.append( (type_name, schema) )

    return sorted(type_list, key = lambda type_name: type_name[0])

def type_info(pk, type_name):
    data = get_data(pk)
    if data is None:
        return None
    schema = build_schema(data,type_name)
    schema0 = [x.split(',')[0] for x in schema]

    k1 = {'intel' : [type_name]*len(schema0)}
    k2 = {'intel': schema0}

    raw_stats = data.aggregate_stats(type_name)[0]

    stats = []
    scale = 1.0
    for t in range(len(raw_stats)):
        temp = []
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event]*scale)
        stats.append((data.times[t],temp))

    tp = plot.DevPlot(k1,k2,lariat_data='pass')
    tp.plot(pk,job_data=data)
    plot_base64 = figure_to_base64(tp)
    return {
                    'type_name':type_name,
                    'job_id': pk,
                    'type_plot':plot_base64,
                    'schema':schema,
                    'stats':stats
                    }

class LS4JobDetailView(DetailView):

    model = LS4Job
    
    def get_context_data(self, **kwargs):
        context = super(LS4JobDetailView, self).get_context_data(**kwargs)
        job = context['ls4job']

        data = get_data(job.id)

        type_list = []
        host_list = []

        for host_name, host in data.hosts.iteritems():
            host_list.append(host_name)
        for type_name, type in host.stats.iteritems():
            schema = ' '.join(build_schema(data,type_name))
            type_list.append( (type_name, schema) )

        type_list = sorted(type_list, key = lambda type_name: type_name[0])
        context['type_list'] = type_list
        context['host_list'] = host_list

        urlstring="https://scribe.tacc.utexas.edu:8000/en-US/app/search/search?q=search%20"
        urlstring+="%20host%3D"+host_list[0]+".ls4.tacc.utexas.edu"

        for host in host_list[1:]:
            urlstring+="%20OR%20%20host%3D"+host+".ls4.tacc.utexas.edu"
            
        urlstring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
            
        context['splunk_url'] = urlstring

        return context
    
