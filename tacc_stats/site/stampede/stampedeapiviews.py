from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView
from django.db.models import Q
import os,sys,pwd

from tacc_stats.site.stampede.models import Job, Host, JobForm
import tacc_stats.cfg as cfg

import tacc_stats.analysis.plot as plots
from tacc_stats.analysis.gen import lariat_utils
from tacc_stats.pickler import job_stats, batch_acct
# Compatibility with old pickle versions
sys.modules['pickler.job_stats'] = job_stats
sys.modules['pickler.batch_acct'] = batch_acct
sys.modules['job_stats'] = job_stats
sys.modules['batch_acct'] = batch_acct

import cPickle as pickle
import time,pytz
from datetime import datetime

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from django.core.cache import cache,get_cache
import traceback
from rest_framework.decorators import api_view
import base64
import json
from cStringIO import StringIO
from django.http import HttpResponse
from rest_framework.response import Response


def sys_plot(request, pk):

    racks = []
    nodes = []
    for host in Host.objects.values_list('name',flat=True).distinct():
        r,n=host.split('-')
        racks.append(r)
        nodes.append(n)
    racks = sorted(set(racks))
    nodes = sorted(set(nodes))

    job = Job.objects.get(id=pk)
    hosts = job.host_set.all().values_list('name',flat=True)

    x = np.zeros((len(nodes),len(racks)))
    for r in range(len(racks)):
        for n in range(len(nodes)):
            name = str(racks[r])+'-'+str(nodes[n])
            if name in hosts: x[n][r] = 1.0

    fig = Figure(figsize=(25,6))
    ax=fig.add_subplot(1,1,1)

    ax.set_yticks(range(len(nodes)))
    ax.set_yticklabels(nodes,fontsize=6)
    ax.set_xticks(range(len(racks)))
    ax.set_xticklabels(racks,fontsize=6,rotation=90)

    pcm = ax.pcolor(np.array(range(len(racks)+1)),np.array(range(len(nodes)+1)),x)

    canvas = FigureCanvas(fig)
    #response = HttpResponse(content_type='image/png')
    #response['Content-Disposition'] = "attachment; filename="+pk+"-sys.png"
    sio = StringIO()
    fig.savefig(sio, format='png')
    return base64.standard_b64encode(sio.getvalue())


def hist_summary(job_list):

    job_list = job_list.exclude(status__in=['CANCELLED','FAILED'])
    fig = Figure(figsize=(16,6))

    # Run times
    job_times = np.array(job_list.values_list('run_time',flat=True))/3600.
    ax = fig.add_subplot(221)
    ax.hist(job_times, max(5, 5*np.log(len(job_list))),log=True)
    ax.set_xlim((0,max(job_times)+1))
    ax.set_ylabel('# of jobs')
    ax.set_xlabel('# hrs')
    ax.set_title('Run Times for Completed Jobs')

    # Number of cores
    job_size =  np.array(job_list.values_list('cores',flat=True))
    ax = fig.add_subplot(222)
    ax.hist(job_size, max(5, 5*np.log(len(job_list))),log=True)
    ax.set_xlim((0,max(job_size)+1))
    ax.set_title('Run Sizes for Completed Jobs')
    ax.set_xlabel('# cores')

    try:
        # CPI
        job_cpi = np.array(job_list.exclude(Q(**{'cpi' : None}) | Q(**{'cpi' : float('nan')})).values_list('cpi',flat=True))
        ax = fig.add_subplot(223)
        mean_cpi = job_cpi.mean()
        var_cpi = job_cpi.var()
        job_cpi = job_cpi[job_cpi<4.0]
        ax.hist(job_cpi, max(5, 5*np.log(len(job_list))),log=True)
        #ax.set_xlim(0,min(job_cpi.max(),4.0))
        ax.set_ylabel('# of jobs')
        ax.set_title('CPI for Successful Jobs over 1 hr '+r'$\bar{Mean}=$'+'{0:.2f}'.format(mean_cpi)+' '+r'$Var=$' +  '{0:.2f}'.format(var_cpi))
        ax.set_xlabel('CPI')
    except: pass
    try:
        # MBW
        job_mbw = np.array(job_list.exclude(Q(**{'mbw' : None}) | Q(**{'mbw' : float('nan')})).values_list('mbw',flat=True))
        ax = fig.add_subplot(224)
        job_mbw = job_mbw[job_mbw < 1.0]
        ax.hist(job_mbw, max(5, 5*np.log(len(job_list))))
        #ax.set_xlim(0,job_mbw.max())
        ax.set_ylabel('# of jobs')
        ax.set_title('MBW for Successful Jobs over 1 hr')
        ax.set_xlabel('MBW')
    except: pass
    fig.subplots_adjust(hspace=0.5)
    canvas = FigureCanvas(fig)

    import StringIO,base64,urllib
    imgdata = StringIO.StringIO()
    fig.savefig(imgdata, format='png')
    imgdata.seek(0)
    response = "data:image/png;base64,%s" % base64.b64encode(imgdata.buf)

    """
    response = HttpResponse(content_type='data:image/png;base64')
    response['Content-Disposition'] = "attachment; filename="+name+"hist.png"
    fig.savefig(response, format='png')
    """

    return response

def figure_to_base64(p):
    sio = StringIO()
    p.fig.savefig(sio, format='png')
    return base64.standard_b64encode(sio.getvalue())

def get_data(pk):
    if cache.has_key(pk):
        data = cache.get(pk)
    else:
        job = Job.objects.get(pk = pk)
        with open(os.path.join(cfg.pickles_dir,job.date.strftime('%Y-%m-%d'),str(job.id)),'rb') as f:
            data = pickle.load(f)
            cache.set(job.id, data)
    return data

def master_plot(request, pk):
    data = get_data(pk)
    mp = plots.MasterPlot(lariat_data="pass")
    mp.plot(pk,job_data=data)
    return figure_to_base64(mp)

def heat_map(request, pk):
    data = get_data(pk)
    hm = plots.HeatMap(k1=['intel_snb','intel_snb'],
                       k2=['CLOCKS_UNHALTED_REF',
                           'INSTRUCTIONS_RETIRED'],
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
    raw_stats = data.aggregate_stats(type_name)[0]
    stats = []
    scale = 1.0
    for t in range(len(raw_stats)):
        temp = []
        times = data.times-data.times[0]
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event]*scale)
        stats.append((times[t],temp))

    k1 = {'intel_snb' : [type_name]*len(schema0)}
    k2 = {'intel_snb': schema0}

    tp = plots.DevPlot(k1=k1,k2=k2,lariat_data='pass')
    tp.plot(pk,job_data=data)
    plot_base64 = figure_to_base64(tp)
    print stats
    print schema
    return {
                    'type_name':type_name,
                    'job_id': pk,
                    'type_plot':plot_base64,
                    'schema':schema,
                    'stats':stats
                    }


class JobDetailView(DetailView):

    model = Job

    def get_context_data(self, **kwargs):
        context = super(JobDetailView, self).get_context_data(**kwargs)
        job = context['job']

        data = get_data(job.id)

        type_list = []
        host_list = []

        for host_name, host in data.hosts.iteritems():
            host_list.append(host_name)
        host0=data.hosts.values()[0]
        for type_name, type in host0.stats.iteritems():
            schema = ' '.join(build_schema(data,type_name))
            type_list.append( (type_name, schema) )

        type_list = sorted(type_list, key = lambda type_name: type_name[0])
        context['type_list'] = type_list
        context['host_list'] = host_list

        urlstring="https://scribe.tacc.utexas.edu:8000/en-US/app/search/search?q=search%20kernel:"
        hoststring=urlstring+"%20host%3D"+host_list[0]
        serverstring=urlstring+"%20mds*%20OR%20%20oss*"
        for host in host_list[1:]:
            hoststring+="%20OR%20%20host%3D"+host

        hoststring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
        serverstring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
        context['client_url'] = hoststring
        context['server_url'] = serverstring

        return context

