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

def update(meta = None, rerun=False):

    ld = lariat_utils.LariatData(directory = '/hpc/tacc_stats_site/lonestar/lariatData',
                                 daysback = 2)
    
    for jobid, json in meta.json.iteritems():
        if rerun:
            if LS4Job.objects.filter(id = jobid).exists():
                job = LS4Job.objects.filter(id = jobid).delete()
                
        obj,created = LS4Job.objects.get_or_create(id = jobid)
        if not created: continue
        
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
        jsondb['submission_time'] = json['submission_time']
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
        try: ld.set_job(jobid,end_time = meta.json[jobid]['end_epoch'])   
        except: pass
        jsondb['exe'] = ld.exc.split('/')[-1]
        jsondb['cwd'] = ld.cwd
        jsondb['threads'] = ld.threads
        
        obj = LS4Job(**jsondb)
        obj.save()

def dates(request):
    
    date_list = os.listdir('/hpc/tacc_stats_site/lonestar/pickles')
    date_list = sorted(date_list, key=lambda d: map(int, d.split('-')))

    month_dict ={}

    for date in date_list:
        y,m,d = date.split('-')
        key = y+' / '+m
        if key not in month_dict: month_dict[key] = []
        date_pair = (date, d)
        month_dict[key].append(date_pair)

    date_list = month_dict
    return render_to_response("lonestar/dates.html", { 'date_list' : sorted(date_list.iteritems())})

def search(request):

    if 'q' in request.GET:
        q = request.GET['q']
        try:
            job = LS4Job.objects.get(id = q)
            return HttpResponseRedirect("/lonestar/job/"+str(job.id)+"/")
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
        field['exe__contains'] = exe

    field['run_time__gte'] = 60 

    job_list = LS4Job.objects.filter(**field).order_by('-id')
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
        field['exe__contains'] = exe
    
    field['run_time__gte'] = 60 
    field['status'] = 'COMPLETED'

    job_list = LS4Job.objects.filter(**field)
    fig = Figure(figsize=(16,6))

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
    canvas = FigureCanvas(fig)
    return figure_to_response(fig)


def figure_to_response(f):
    response = HttpResponse(content_type='image/png')
    f.savefig(response, format='png')
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
    mp = plot.MasterPlot(lariat_data="pass")
    mp.plot(pk,job_data=data)
    return figure_to_response(mp.fig)

def heat_map(request, pk):
    
    data = get_data(pk)
    hm = plot.HeatMap({'intel' : ['intel_pmc3','intel_pmc3']},
                          {'intel' : ['CLOCKS_UNHALTED_REF',
                                      'INSTRUCTIONS_RETIRED']},
                          lariat_data="pass")
    hm.plot(pk,job_data=data)
    return figure_to_response(hm.fig)

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

        urlstring="https://scribe.tacc.utexas.edu:8000/en-US/app/search/search?q=search%20"
        urlstring+="%20host%3D"+host_list[0]+".ls4.tacc.utexas.edu"

        for host in host_list[1:]:
            urlstring+="%20OR%20%20host%3D"+host+".ls4.tacc.utexas.edu"
            
        urlstring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
            
        context['splunk_url'] = urlstring

        return context

def type_plot(request, pk, type_name):
    data = get_data(pk)

    schema = build_schema(data,type_name)
    schema = [x.split(',')[0] for x in schema]

    k1 = {'intel' : [type_name]*len(schema)}
    k2 = {'intel': schema}

    tp = plot.DevPlot(k1,k2,lariat_data='pass')
    tp.plot(pk,job_data=data)
    return figure_to_response(tp.fig)


def type_detail(request, pk, type_name):

    data = get_data(pk)

    schema = build_schema(data,type_name)
    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []
    scale = 1.0
    for t in range(len(raw_stats)):
        temp = []
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event]*scale)
        stats.append((data.times[t],temp))


    return render_to_response("lonestar/type_detail.html",{"type_name" : type_name, "jobid" : pk, "stats_data" : stats, "schema" : schema})
    
