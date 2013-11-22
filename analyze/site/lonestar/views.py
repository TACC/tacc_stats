from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView
import matplotlib, string
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pylab import figure, hist, plot

from lonestar.models import LS4Job, LS4JobForm
import sys_path_append
import os,sys
import masterplot as mp
import plotkey, tspl, lariat_utils
import job_stats as data
import MetaData
import cPickle as pickle 
import time
   
import numpy as np

from django.core.cache import cache,get_cache 

path = sys_path_append.pickles_dir

def ls4_update(meta = None):
    if not meta: return

    #LS4Job.objects.all().delete()

    # Only need to populate lariat cache once
    jobid = meta.json.keys()[0]

    ld = lariat_utils.LariatData(jobid,
                                 end_epoch = meta.json[jobid]['end_epoch'],
                                 directory = sys_path_append.lariat_path,
                                 daysback = 2)
        
    for jobid, json in meta.json.iteritems():

        if LS4Job.objects.filter(id = jobid).exists(): continue  
        ld = lariat_utils.LariatData(jobid,
                                     olddata = ld.ld)

        if json['exit_status'] != 0: json['status'] = 'TIMEOUT/CANCELLED'
        else: json['status'] = 'COMPLETED'
        if json['failed'] != 0: json['status'] = 'FAILED'

        json['nodes'] = str(int(json['slots'])/12)
        json['cores'] = str(int(json['granted_pe'].rstrip('way'))*int(json['nodes']))
        json['run_time'] = meta.json[jobid]['end_epoch'] - meta.json[jobid]['start_epoch']

        jsondb = {}
        jsondb['id'] = json['id']
        jsondb['project'] = json['account']
        jsondb['start_time'] = json['start_time']
        jsondb['end_time'] = json['end_time']
        jsondb['start_epoch'] = json['start_epoch']
        jsondb['end_epoch'] = json['end_epoch']
        jsondb['run_time'] = json['run_time']
        jsondb['queue'] = json['queue']
        jsondb['name'] = json['name']
        jsondb['status'] = json['status']
        jsondb['nodes'] = json['nodes']
        jsondb['cores'] = json['cores']
        jsondb['path'] = json['path']
        jsondb['date'] = json['date']
        jsondb['user'] = json['owner']

        # LD
        jsondb['exe'] = ld.exc.split('/')[-1]
        jsondb['cwd'] = ld.cwd
        jsondb['threads'] = ld.threads
        
        
        try:
            job_model, created = LS4Job.objects.get_or_create(**jsondb) 
        except:
            print "Something wrong with json",jsondb
    return 


def dates(request):
    
    date_list = os.listdir(path)
    date_list = sorted(date_list, key=lambda d: map(int, d.split('-')))

    month_dict ={}

    for date in date_list:
        y,m,d = date.split('-')
        key = y+' / '+m
        if key not in month_dict: month_dict[key] = []
        date_pair = (date, d)
        month_dict[key].append(date_pair)

    date_list = month_dict
    return render_to_response("lonestar/dates.html", { 'date_list' : date_list})

def search(request):

    if 'q' in request.GET:
        q = request.GET['q']
        try:
            job = LS4Job.objects.get(id = q)
            return HttpResponseRedirect("/job/"+str(job.id)+"/")
        except: pass

    if 'u' in request.GET:
        u = request.GET['u']
        try:
            return index(request, user = u)
        except: pass

    if 'n' in request.GET:
        user = request.GET['n']
        try:
            return index(request, user = user)
        except: pass

    if 'p' in request.GET:
        project = request.GET['p']
        try:
            return index(request, project = project)
        except: pass

    if 'x' in request.GET:
        x = request.GET['x']
        try:
            return index(request, exe = x)
        except: pass

    return render(request, 'lonestar/dates.html', {'error' : True})


def index(request, date = None, project = None, user = None, exe = None):

    field = {}
    if date:
        field['date'] = date
    if user:
        field['user'] = user
    if project:
        field['project'] = project
    if exe:
        field['exe'] = exe

    if exe:
        job_list = LS4Job.objects.filter(exe__contains=exe).filter(run_time__gte=60).order_by('-id')[0::1]
    else:
        job_list = LS4Job.objects.filter(**field).filter(run_time__gte=60).order_by('-id')[0::1]
    field['job_list'] = job_list
    field['nj'] = len(job_list)

    return render_to_response("lonestar/index.html", field)

def hist_summary(request, date = None, project = None, user = None, exe = None):

    field = {}
    if date:
        field['date'] = date
    if user:
        field['user'] = user
    if project:
        field['project'] = project
    if exe:
        field['exe'] = exe
        
    field['status'] = 'COMPLETED'

    if exe:
        job_list = LS4Job.objects.filter(exe__contains=exe).filter(run_time__gte=60)[0::1]
    else:
        job_list = LS4Job.objects.filter(**field).filter(run_time__gte=60)[0::1]
    fig = figure(figsize=(16,6))

    # Run times
    job_times = np.array([job.run_time for job in job_list])/3600.
    ax = fig.add_subplot(121)
    ax.hist(job_times, max(5, 5*np.log(len(job_list))))
    ax.set_xlim((0,max(job_times)+1))
    ax.set_ylabel('# of jobs')
    ax.set_xlabel('# hrs')
    ax.set_title('Run Times for Completed Jobs')

    # Number of cores
    job_size = [job.cores for job in job_list]
    ax = fig.add_subplot(122)
    ax.hist(job_size, max(5, 5*np.log(len(job_list))))
    ax.set_xlim((0,max(job_size)+1))
    ax.set_title('Run Sizes for Completed Jobs')
    ax.set_xlabel('# cores')

    return figure_to_response(fig)


def figure_to_response(f):
    response = HttpResponse(content_type='image/svg+xml')
    f.savefig(response, format='svg')
    plt.close(f)
    f.clear()
    return response

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
    
    fig, fname = mp.master_plot(None,header=None,mintime=60,wayness=int(data.acct['granted_pe'].rstrip('way')),lariat_dict="pass",job_stats=data)
    return figure_to_response(fig)

def heat_map(request, pk):
    
    data = get_data(pk)

    k1 = {'intel' : ['intel_pmc3']}

    k2 = {'intel': ['MEM_LOAD_RETIRED_L1D_HIT']}
    #k2 = {'intel': ['INSTRUCTIONS_RETIRED']}
    ts0 = tspl.TSPLBase(None,k1,k2,job_stats = data)

    k2 = {'intel': ['CLOCKS_UNHALTED_CORE']}
    ts1 = tspl.TSPLBase(None,k1,k2,job_stats = data)

    cpi = np.array([])
    hosts = []
    for v in ts0.data[0]:
        hosts.append(v)
        ncores = len(ts0.data[0][v])
        for k in range(ncores):
            i = np.array(ts0.data[0][v][k],dtype=np.float)
            c = np.array(ts1.data[0][v][k],dtype=np.float)
            ratio = np.divide(np.diff(i),np.diff(c))
            if not cpi.size: cpi = np.array([ratio])
            else: cpi = np.vstack((cpi,ratio))
    cpi_min, cpi_max = cpi.min(), cpi.max()

    fig,ax=plt.subplots(1,1,figsize=(8,12),dpi=110)

    ycore = np.arange(cpi.shape[0]+1)
    time = ts0.t/3600.

    yhost=np.arange(len(hosts)+1)*ncores + ncores    

    fontsize = 10

    if len(yhost) > 80:
        fontsize /= 0.5*np.log(len(yhost))
        
    plt.yticks(yhost - ncores/2.,hosts,size=fontsize) 
    plt.pcolormesh(time, ycore, cpi, vmin=cpi_min, vmax=cpi_max)
    plt.axis([time.min(),time.max(),ycore.min(),ycore.max()])

    plt.title('L1D Load Hits per Core Clock Cycle')
    plt.colorbar()

    ax.set_xlabel('Time (hrs)')

    plt.close()

    return figure_to_response(fig)

def build_schema(data,name):
    schema = []
    for key,value in data.get_schema(name).iteritems():
        if value.unit:
            schema.append(value.key + ','+value.unit)
        else: schema.append(value.key)
    return schema

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

        return context

def type_plot(request, pk, type_name):
    data = get_data(pk)

    schema = build_schema(data,type_name)
    schema = [x.split(',')[0] for x in schema]

    k1 = {'intel' : [type_name]*len(schema)}
    k2 = {'intel': schema}

    ts = tspl.TSPLSum(None,k1,k2,job_stats=data)
    
    nr_events = len(schema)
    fig, axarr = plt.subplots(nr_events, sharex=True, figsize=(8,nr_events*2), dpi=80)
    do_rate = True
    for i in range(nr_events):
        if type_name == 'mem': do_rate = False

        mp.plot_lines(axarr[i], ts, [i], 3600., do_rate = do_rate)
        axarr[i].set_ylabel(schema[i],size='small')
    axarr[-1].set_xlabel("Time (hr)")
    fig.subplots_adjust(hspace=0.0)
    fig.tight_layout()

    return figure_to_response(fig)


def type_detail(request, pk, type_name):

    data = get_data(pk)

    schema = build_schema(data,type_name)
    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []
    for t in range(len(raw_stats)):
        temp = []
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event])
        stats.append((data.times[t],temp))


    return render_to_response("lonestar/type_detail.html",{"type_name" : type_name, "jobid" : pk, "stats_data" : stats, "schema" : schema})
    
