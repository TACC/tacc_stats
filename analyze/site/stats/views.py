from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView
import matplotlib, string
import matplotlib.pyplot as plt
from pylab import figure, hist, plot

from stats.models import Job, JobForm
import sys_path_append
import os,sys
import masterplot as mp
import plotkey
import tspl
import job_stats as data
import MetaData
import cPickle as pickle 



path = sys_path_append.pickles_dir

def dates(request):
    date_list = []
    import time
    #Job.objects.all().delete()
    for date in os.listdir(path):
        print 'Date',date
        start = time.clock()
        date_list.append(date)
        meta = MetaData.MetaData(os.path.join(path,date))    
        meta.load_update()

        start = time.clock()
        for jobid, json in meta.json.iteritems():
            if Job.objects.filter(id = jobid).exists(): continue
            job_model, created = Job.objects.get_or_create(**json) 

    return render_to_response("stats/dates.html", { 'date_list' : date_list})

def search(request):

    if 'q' in request.GET:
        q = request.GET['q']
        message = 'You searched for: %r' % request.GET['q']
        try:
            job = Job.objects.get(id = q)
            return HttpResponseRedirect("/stats/job/"+str(job.id)+"/")
        except: pass

    if 'u' in request.GET:
        u = request.GET['u']
        message = 'You searched for: %r' % request.GET['u']
        try:
            return index(request, uid = u)
        except: pass

    return render(request, 'stats/dates.html', {'error' : True})


def index(request, date = None, uid = None, project = None):

    field = {}
    if date:
        field['date'] = date
    if uid:
        field['uid'] = uid
    if project:
        field['project'] = project
        
    job_list = Job.objects.filter(**field).order_by('-id')

    field['job_list'] = job_list
    field['nj'] = len(job_list)
    
    
    return render_to_response("stats/index.html", field)

def hist_summary(request, date = None, uid = None, project = None):

    field = {}
    if date:
        field['date'] = date
    if uid:
        field['uid'] = uid
    if project:
        field['project'] = project
        
    field['status'] = 'COMPLETED'

    job_list = Job.objects.filter(**field)

    fig = figure(figsize=(12,6))

    # Run times
    job_times = [job.timespent / 3600. for job in job_list]
    ax = fig.add_subplot(121)
    ax.hist(job_times, max(5, len(job_list)/5))
    ax.set_xlim((0,max(job_times)+1))
    ax.set_ylabel('# of jobs')
    ax.set_xlabel('# hrs')
    
    # Number of cores
    job_size = [job.cores for job in job_list]
    ax = fig.add_subplot(122)
    ax.hist(job_size, max(5, len(job_list)/5))
    ax.set_xlim((0,max(job_size)+1))
    ax.set_title('Run Sizes for Completed Jobs')
    ax.set_xlabel('# cores')

    ax.set_title('Run Times for Completed Jobs')

    fig.tight_layout()

    return figure_to_response(fig)

def stats_load(job):
    with open(job.path) as f:
        job.stats = pickle.load(f)
    job.save()

def get_schema(job, type_name):
    with open(job.path) as f:
        data = pickle.load(f)
    schema = data.get_schema(type_name).desc
    schema = string.replace(schema,',E',' ')
    schema = string.replace(schema,' ,',',').split()
    schema = [x.split(',')[0] for x in schema]

    return schema


def figure_to_response(f):
    response = HttpResponse(content_type='image/png')
    f.savefig(response, format='png')
    plt.close(f)
    f.clear()
    return response

def stats_unload(job):
    job.stats = []
    job.save()

def master_plot(request, pk):
    job = Job.objects.get(id = pk)
    fig, fname = mp.master_plot(job.path,mintime=600)
    return figure_to_response(fig)

def heat_map(request, pk):
    job = Job.objects.get(id = pk)
    
    import numpy as np
    k1 = {'intel_snb' : ['intel_snb']}
    k2 = {'intel_snb': ['INSTRUCTIONS_RETIRED']}
    ts0 = tspl.TSPLBase(job.path,k1,k2)

    k1 = {'intel_snb' : ['intel_snb']}
    k2 = {'intel_snb': ['CLOCKS_UNHALTED_CORE']}
    ts1 = tspl.TSPLBase(job.path,k1,k2)

    tmid=(ts0.t[:-1]+ts0.t[1:])/2.0

    cpi = np.array([])
    hosts = []
    for v in ts0.data[0]:
        hosts.append(v)
        for k in range(len(ts0.data[0][v])):
            i = np.array(ts0.data[0][v][k],dtype=np.float)
            c = np.array(ts1.data[0][v][k],dtype=np.float)
            ratio = np.divide(np.diff(i),np.diff(c))
            if not cpi.size: cpi = np.array([ratio])
            else: cpi = np.vstack((cpi,ratio))

    cpi_min, cpi_max = cpi.min(), cpi.max()
    fig,ax=plt.subplots(1,1,figsize=(8,12),dpi=160)

    y=np.arange(len(hosts)+1)*16
    
    yfine = np.arange(cpi.shape[0]+1)
    
    time = tmid/3600.
    print cpi.shape,yfine.shape
    
    for l in range(len(y)):
        plt.axhline(y=y[l]+16, linewidth=0.5,color='black',linestyle='--')


    plt.pcolor(time, yfine, cpi, vmin=cpi_min, vmax=cpi_max)
    plt.colorbar()
    plt.clim(cpi_min,cpi_max)
    plt.yticks(y+8,hosts,size='small')
    plt.title('Instructions Retired per Core Clock Cycle')
    plt.axis([time.min(),time.max(),yfine.min(),yfine.max()])
    ax.set_xlabel('Time (hrs)')
    plt.tight_layout()
    plt.close()

    return figure_to_response(fig)

class JobDetailView(DetailView):

    model = Job
    
    def get_context_data(self, **kwargs):
        context = super(JobDetailView, self).get_context_data(**kwargs)
        job = context['job']
        stats_load(job)
        type_list = []
        host_list = []
        for host_name, host in job.stats.hosts.iteritems():
            host_list.append(host_name)
        for type_name, type in host.stats.iteritems():
            schema = job.stats.get_schema(type_name).desc
            schema = string.replace(schema,',E',' ')
            schema = string.replace(schema,',',' ')
            type_list.append( (type_name, schema) )

        type_list = sorted(type_list, key = lambda type_name: type_name[0])
        context['type_list'] = type_list
        context['host_list'] = host_list
        stats_unload(job)
        return context

def type_plot(request, pk, type_name):

    job = Job.objects.get(id = pk)
    schema = get_schema(job, type_name)

    k1 = {'intel_snb' : [type_name]*len(schema)}
    k2 = {'intel_snb': schema}

    ts = tspl.TSPLSum(job.path,k1,k2)
    
    nr_events = len(schema)
    fig, axarr = plt.subplots(nr_events, sharex=True, figsize=(8,nr_events*2), dpi=80)
    do_rate = True
    for i in range(nr_events):
        if type_name == 'mem': do_rate = False
        axarr[i].set_ylabel(schema[i],size='small')
        mp.plot_lines(axarr[i], ts, [i], 3600., do_rate = do_rate)

    axarr[-1].set_xlabel("Time (hr)")
    fig.subplots_adjust(hspace=0.0)
    fig.tight_layout()
    response = HttpResponse(content_type='image/png')
    fig.savefig(response, format='png')
    plt.close(fig)
    fig.clear()

    return response


def type_detail(request, pk, type_name):

    job = Job.objects.get(id = pk)
    stats_load(job)
    data = job.stats

    schema = data.get_schema(type_name).desc
    schema = string.replace(schema,',E',' ')
    schema = string.replace(schema,' ,',',').split()

    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []
    for t in range(len(raw_stats)):
        temp = []
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event])
        stats.append((data.times[t],temp))

    stats_unload(job)

    return render_to_response("stats/type_detail.html",{"type_name" : type_name, "jobid" : pk, "stats_data" : stats, "schema" : schema})
    
