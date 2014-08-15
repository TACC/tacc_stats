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

def update(date,rerun=False):

    ld = lariat_utils.LariatData(directory = cfg.lariat_path,
                                 daysback = 2)

    tz = pytz.timezone('US/Central')

    pickle_dir = os.path.join(cfg.pickles_dir,date)

    ctr = 0

    for root, directory, pickle_files in os.walk(pickle_dir):
        num_files = len(pickle_files)
        print "Number of pickle files in",root,'=',num_files
        for pickle_file in sorted(pickle_files):
            ctr += 1
            print pickle_file
            try:
                if rerun:
                    if Job.objects.filter(id = pickle_file).exists():
                        job = Job.objects.filter(id = pickle_file).delete()
            
                obj,created = Job.objects.get_or_create(id = pickle_file)
            except: 
                print pickle_file,"doesn't look like a pickled job"
                continue
            if not created: 
                if len(obj.host_set.all()) > 0: 
                    continue 
                try:
                    pickle_path = os.path.join(root,str(pickle_file))
                    with open(pickle_path, 'rb') as f:
                        hosts = np.load(f).hosts.keys()
                        for host_name in hosts:
                            h = Host(name=host_name)
                            h.save()
                            h.jobs.add(obj)
                except: pass
                continue

            try:

                pickle_path = os.path.join(root,str(pickle_file))
                with open(pickle_path, 'rb') as f:
                    data = np.load(f)
                    json = data.acct
                    hosts = data.hosts.keys()

                del json['yesno'], json['unknown']
                json['run_time'] = json['end_time'] - json['start_time']

                json['path'] = pickle_path
                json['start_epoch'] = json['start_time']
                json['end_epoch'] = json['end_time']
                        
                utc_start = datetime.utcfromtimestamp(json['start_time']).replace(tzinfo=pytz.utc)
                utc_end = datetime.utcfromtimestamp(json['end_time']).replace(tzinfo=pytz.utc)
                json['start_time'] = utc_start.astimezone(tz)
                json['end_time'] =  utc_end.astimezone(tz)
                json['date'] = json['end_time'].date()
                
                ld.set_job(pickle_file, end_time = date)
                
                json['exe'] = ld.exc.split('/')[-1]
                json['cwd'] = ld.cwd[0:128]
                json['threads'] = ld.threads
                json['name'] = json['name'][0:128]
                if ld.cores: json['cores'] = ld.cores
                if ld.nodes: json['nodes'] = ld.nodes
                if ld.wayness: json['wayness'] = ld.wayness

                try: json['user']=pwd.getpwuid(int(json['uid']))[0]
                except: json['user']=ld.user

                obj = Job(**json)
                obj.save()

                for host_name in hosts:
                    h = Host(name=host_name)
                    print host_name
                    h.save()
                    h.jobs.add(obj)

            except: 
                print json
                print pickle_file,'failed'
                print traceback.format_exc()
                print date
            print "Percentage Completed =",100*float(ctr)/num_files

def update_test_field(date,test,metric,rerun=False):
    print "Run",test.__class__.__name__,"test for",date
    
    kwargs = { 'date' : date, 
               'run_time__gte' : test.min_time,
               'nodes__gte' : test.min_hosts
               }
    
    jobs_list = Job.objects.filter(**kwargs).exclude(Q(queue__in=test.ignore_qs) | Q(status__in = test.ignore_status))

    if not rerun:
        jobs_list = jobs_list.filter(Q(**{metric : None}) | Q(**{metric : float('nan')}))

    paths = []
    for job in jobs_list:
        paths.append(os.path.join(cfg.pickles_dir,job.date.strftime('%Y-%m-%d'),str(job.id)))

    print '# Jobs to be tested:',len(jobs_list)
    test.run(paths)
    for jid in test.results.keys(): 
        jobs_list.filter(id = jid).update(**{metric : test.results[jid]['metric']})


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
    response = HttpResponse(content_type='image/png')
    response['Content-Disposition'] = "attachment; filename="+pk+"-sys.png"
    fig.savefig(response, format='png')

    return response


def dates(request):
    
    date_list = os.listdir(cfg.pickles_dir)
    date_list = sorted(date_list, key=lambda d: map(int, d.split('-')))

    month_dict ={}

    for date in date_list:
        y,m,d = date.split('-')
        key = y+' / '+m
        if key not in month_dict: month_dict[key] = []
        date_pair = (date, d)
        month_dict[key].append(date_pair)

    date_list = month_dict
    field = {}
    # Computed Metrics
    """
    completed_list = Job.objects.filter(run_time__gte = 3600,date__year = 2014).exclude(status__in=['CANCELLED','FAILED'])
    
    field['cpi_thresh'] = 0.75
    field['cpi_job_list']  = completed_list.exclude(Q(cpi = float('nan')) | Q(cpi = None) ).filter(cpi__gte = field['cpi_thresh'])
    field['cpi_per'] = 100*len(field['cpi_job_list'])/float(len(completed_list))
    """
    field['date_list'] = sorted(date_list.iteritems())
    return render_to_response("stampede/dates.html", field)

def search(request):

    if 'q' in request.GET:
        q = request.GET['q']
        try:
            job = Job.objects.get(id = q)
            return HttpResponseRedirect("/stampede/job/"+str(job.id)+"/")
        except: pass

    if 'u' in request.GET:
        u = request.GET['u']
        try:
            return index(request, uid = u)
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

    return render(request, 'stampede/dates.html', {'error' : True})

def index(request, date = None, uid = None, project = None, user = None, exe = None, report=None):
    
    field = {}
    name = ''
    if date:
        name+=date+'-'
        field['date'] = date
    if uid:
        name+=uid+'-'
        field['uid'] = uid
    if user:
        name+=user+'-'
        field['user'] = user
    if project:
        name+=project+'-'
        field['project'] = project
    if exe:
        name+=exe+'-'
        field['exe__icontains'] = exe

    field['run_time__gte'] = 60 

    job_list = Job.objects.filter(**field).order_by('-id')

    field['job_list'] = job_list
    field['nj'] = len(job_list)

    # Computed Metrics
    field['cat_job_list']  = job_list.filter(Q(cat__lte = 0.001) | Q(cat__gte = 1000)).exclude(cat = float('nan'))
    
    completed_list = job_list.exclude(status__in=['CANCELLED','FAILED']).order_by('-id')
    field['idle_job_list'] = completed_list.filter(idle__gte = 0.99)
    field['mem_job_list'] = completed_list.filter(mem__gte = 30)

    field['cpi_thresh'] = 1.0
    field['cpi_job_list']  = completed_list.exclude(cpi = float('nan')).filter(cpi__gte = field['cpi_thresh'])
    field['cpi_per'] = 100*len(field['cpi_job_list'])/float(len(completed_list))

    field['idle_job_list'] = list_to_dict(field['idle_job_list'],'idle')
    field['cat_job_list'] = list_to_dict(field['cat_job_list'],'cat')
    field['cpi_job_list'] = list_to_dict(field['cpi_job_list'],'cpi')
    field['mem_job_list'] = list_to_dict(field['mem_job_list'],'mem')

    if report: 
        field['report'] = report 
        field['name'] = name 
        return render_to_pdf("stampede/index.html", field)
    else:  return render_to_response("stampede/index.html", field)

def list_to_dict(job_list,metric):
    job_dict={}
    for job in job_list:
        job_dict.setdefault(job.user,[]).append((job.id,round(job.__dict__[metric],3)))
    return job_dict
    

def hist_summary(request, date = None, uid = None, project = None, user = None, exe = None, report = None):

    field = {}
    name = ''
    if date:
        field['date'] = date
        name+=date+'-'
    if uid:
        field['uid'] = uid
        name+=uid+'-'
    if user:
        field['user'] = user
        name+=user+'-'
    if project:
        field['project'] = project
        name+=project+'-'
    if exe:
        field['exe__icontains'] = exe
        name+=exe+'-'

    field['run_time__gte'] = 60 

    job_list = Job.objects.filter(**field).exclude(status__in=['CANCELLED','FAILED'])
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
    
    if report:
        response = HttpResponse(content_type='image/pdf')
        response['Content-Disposition'] = "attachment; filename="+name+"hist.pdf"
        fig.savefig(response, format='pdf')
    else:
        response = HttpResponse(content_type='image/png')
        response['Content-Disposition'] = "attachment; filename="+name+"hist.png"
        fig.savefig(response, format='png')

    return response

def figure_to_response(p):
    response = HttpResponse(content_type='image/png')
    response['Content-Disposition'] = "attachment; filename="+p.fname+".png"
    p.fig.savefig(response, format='png')
    return response

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
    return figure_to_response(mp)

def heat_map(request, pk):    
    data = get_data(pk)
    hm = plots.HeatMap(k1=['intel_snb','intel_snb'],
                       k2=['CLOCKS_UNHALTED_REF',
                           'INSTRUCTIONS_RETIRED'],
                       lariat_data="pass")
    hm.plot(pk,job_data=data)
    return figure_to_response(hm)

def build_schema(data,name):
    schema = []
    for key,value in data.get_schema(name).iteritems():
        if value.unit:
            schema.append(value.key + ','+value.unit)
        else: schema.append(value.key)
    return schema

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

def type_plot(request, pk, type_name):
    data = get_data(pk)

    schema = build_schema(data,type_name)
    schema = [x.split(',')[0] for x in schema]

    k1 = {'intel_snb' : [type_name]*len(schema)}
    k2 = {'intel_snb': schema}

    tp = plots.DevPlot(k1=k1,k2=k2,lariat_data='pass')
    tp.plot(pk,job_data=data)
    return figure_to_response(tp)


def type_detail(request, pk, type_name):
    data = get_data(pk)

    schema = build_schema(data,type_name)
    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []
    scale = 1.0
    for t in range(len(raw_stats)):
        temp = []
        times = data.times-data.times[0]
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event]*scale)
        stats.append((times[t],temp))

    return render_to_response("stampede/type_detail.html",{"type_name" : type_name, "jobid" : pk, "stats_data" : stats, "schema" : schema})

"""
from django.template.loader import get_template
from django.template import Context
import ho.pisa as pisa
import cStringIO as StringIO
import cgi

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    
    result = StringIO.StringIO()
    
    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), dest=result)
    
    response = HttpResponse(result.getvalue(), \
                                mimetype='application/pdf',)
    
    response['Content-Disposition'] = "attachment; filename="+context_dict['name']+"report.pdf"

    return response
"""
