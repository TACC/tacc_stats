from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import DetailView, ListView
from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.core.cache import cache 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import os,sys,pwd
import pickle as p

from tacc_stats.analysis.metrics import metrics
from tacc_stats.site.machine.models import Job, Host, Libraries
from tacc_stats.site.xalt.models import run, join_run_object, lib
import tacc_stats.cfg as cfg
import tacc_stats.analysis.plot as plots

from datetime import datetime, timedelta

from numpy import array, histogram, log, linspace

from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.plotting import figure
from bokeh.models import HoverTool

#try:
from tacc_stats.site.machine.agave_auth import check_for_tokens
#except:
#pass

"""
racks = set()
nodes = set()
hosts = set()
for host in Host.objects.values_list('name', flat=True).distinct():
    try:
        r, n = host.split('-')
        racks.update({r})
        nodes.update({n})
    except:
        pass
    hosts.update({host})
racks = sorted(list(racks))
nodes = sorted(list(nodes))
hosts = sorted(list(hosts))
"""
"""
sys_color = []
import time
start = time.time()        
for rack in racks:
    for node in nodes:
        name = str(rack)+'-'+str(node)
        if name in hosts: 
            sys_color += ["#002868"]
        else:
            sys_color += ["lavender"]
print "sys setup",time.time()-start
xrack = [r for rack in racks for r in [rack]*len(nodes)]
yrack = nodes*len(racks)
 """
def sys_plot(pk):

    job = Job.objects.get(id=pk)
    jh = job.host_set.all().values_list('name', flat=True).distinct()

    hover = HoverTool(tooltips = [ ("host", "@x-@y") ])
    plot = figure(title = "System Plot", tools = [hover], 
                  toolbar_location = None,
                  x_range = racks, y_range = nodes, 
                  plot_height = 800, plot_width = 1000)

    import time
    start = time.time()
    ctr = 0
    for rack in racks:
        for node in nodes:
            name = str(rack)+'-'+str(node)
            if name in jh: 
                sys_color[ctr] = ["#bf0a30"] 
            ctr+=1
    print("sys",time.time()-start)
    plot.xaxis.major_label_orientation = "vertical"
    plot.rect(xrack, yrack, 
              color = sys_color, width = 1, height = 1)    

    return components(plot)

def dates(request, error = False):
    field = {}
    #try:
    if not check_for_tokens(request):
        return HttpResponseRedirect("/login_prompt")
    field['username'] = request.session['username']
    field['is_staff'] = request.session['is_staff']
    field['email'] = request.session['email']
    field['logged_in'] = True
    #except: pass

    job_objects = Job.objects
    if "is_staff" in request.session and not request.session["is_staff"]:
        job_objects = job_objects.filter(user = request.session["username"])

    month_dict ={}
    date_list = job_objects.exclude(date = None).exclude(date__lt = datetime.today() - timedelta(days = 90)).values_list('date',flat=True).distinct()

    for date in sorted(date_list):
        y,m,d = date.strftime('%Y-%m-%d').split('-')
        key = y+'-'+m
        month_dict.setdefault(key, [])
        month_dict[key].append((y+'-'+m+'-'+d, d))

    field["machine_name"] = cfg.host_name_ext

    field['md_job_list'] = job_objects.filter(date__gt = datetime.today() - timedelta(days = 5)).exclude(avg_openclose__isnull = True ).annotate(io = ExpressionWrapper(F('avg_openclose')*F('nodes'), output_field = FloatField())).order_by('-io')

    try:
        field['md_job_list'] = field['md_job_list'][0:10]
    except: pass    
    field['md_job_list'] = list_to_dict(field['md_job_list'],'io')

    field['date_list'] = sorted(month_dict.items())[::-1]
    field['error'] = error
    return render(request, "machine/search.html", field)

def search(request):

    if 'jobid' in request.GET:
        try:
            job_objects = Job.objects
            if "is_staff" in request.session and not request.session["is_staff"]:
                job_objects = job_objects.filter(user = request.session["username"])
            job = job_objects.get(id = request.GET['jobid'])
            return HttpResponseRedirect("/machine/job/"+str(job.id)+"/")
        except: pass
    try:
        return index(request)
    except: pass

    return dates(request, error = True)
    

def index(request, **kwargs):

    fields = request.GET.dict()
    fields = { k:v for k, v in fields.items() if v }
    fields.update(kwargs)

    metrics = []
    if 'page' in fields: del fields['page']
    if 'opt_field1' in fields.keys() and 'value1' in fields.keys():
        fields[fields['opt_field1']] = fields['value1']
        metrics += [fields['opt_field1']]
        del fields['opt_field1'], fields['value1']
    if 'opt_field2' in fields.keys() and 'value2' in fields.keys():
        fields[fields['opt_field2']] = fields['value2']
        metrics += [fields['opt_field2']]
        del fields['opt_field2'], fields['value2']
    if 'opt_field3' in fields.keys() and 'value3' in fields.keys():
        fields[fields['opt_field3']] = fields['value3']
        metrics += [fields['opt_field3']]
        del fields['opt_field3'], fields['value3']

    name = ''
    for key, val in fields.items():
        name += key+'='+val+'\n'

    order_key = '-id'
    if 'order_key' in fields: 
        order_key = fields['order_key']
        del fields['order_key']
        
    if "date" in fields: 
        date = fields['date'].split('-')
        if len(date) == 2:
            fields['date__year'] = date[0]
            fields['date__month'] = date[1]
            del fields['date']

    job_objects = Job.objects
    if "is_staff" in request.session and not request.session["is_staff"]:
        job_objects = job_objects.filter(user = request.session["username"])

    job_list = job_objects.filter(**fields).distinct().order_by(order_key)
    fields['name'] =  'Query [fields=values] ' + name.rstrip('-')    

    paginator = Paginator(job_list,100)
    page = request.GET.get('page')
    print(page)
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)

    fields['job_list'] = jobs
    fields['nj'] = job_list.count()
    if metrics:
        hists = []
        for m in metrics: hists += [job_hist(job_list, m.split('__')[0], "")]
        fields["script"], fields["div"] = components(gridplot(hists, ncols = len(metrics), plot_height=200, plot_width=400))
    else:
        job_list = job_list.annotate(queue_wait = F("start_epoch") - F("queue_time"))
        fields["script"], fields["div"] = components(gridplot([job_hist(job_list, "run_time", "Hours", 
                                                                        scale = 3600),
                                                               job_hist(job_list, "nodes", "# Nodes"),
                                                               job_hist(job_list, "queue_wait", "Hours", 
                                                                        scale = 3600),
                                                               job_hist(job_list, "avg_openclose", "iops")], 
                                                            ncols = 2,
                                                              plot_width = 400, plot_height = 200))

    # Computed Metrics    
    job_list = job_list.filter(run_time__gt = 600).exclude(queue__in = ["development"])
    fields['cat_job_list']  = job_list.filter(Q(time_imbalance__lte = 0.001) | \
                                              Q(time_imbalance__gte = 1000)).exclude(time_imbalance = float('nan'))

    completed_list = job_list.exclude(status__in=['CANCELLED','FAILED']).order_by('-id')
    if len(completed_list) > 0:
        fields['md_job_list'] = job_list.exclude(avg_openclose__isnull = True ).order_by('-avg_openclose')
        try:
            fields['md_job_list'] = fields['md_job_list'][0:10]
        except: pass

        fields['idle_job_list'] = completed_list.filter(node_imbalance__gte = 0.99)
        fields['cpu_job_list'] = completed_list.filter(avg_cpuusage__lte = 10)
        fields['cpi_thresh'] = 3.0
        fields['cpi_job_list']  = completed_list.exclude(avg_cpi = float('nan')).filter(avg_cpi__gte = fields['cpi_thresh'])
        fields['cpi_per'] = 100*fields['cpi_job_list'].count()/float(completed_list.count())

        fields['gigebw_thresh'] = 1
        fields['gigebw_job_list']  = completed_list.exclude(avg_ethbw = float('nan')).filter(avg_ethbw__gte = fields['gigebw_thresh'])

        fields['md_job_list'] = list_to_dict(fields['md_job_list'],'avg_openclose')
        fields['idle_job_list'] = list_to_dict(fields['idle_job_list'],'node_imbalance')
        fields['cat_job_list'] = list_to_dict(fields['cat_job_list'],'time_imbalance')
        fields['cpi_job_list'] = list_to_dict(fields['cpi_job_list'],'avg_cpi')
        fields['gigebw_job_list'] = list_to_dict(fields['gigebw_job_list'],'avg_ethbw')
    
    if '?' in request.get_full_path():
        fields['current_path'] = request.get_full_path()
    return render(request, "machine/index.html", fields)

def list_to_dict(job_list, metric):
    job_dict={}
    for job in job_list:
        job_dict.setdefault(job.user,[]).append((job.id,round(job.__dict__[metric],3)))
    return job_dict
    
def job_hist(job_list, value, units, scale = 1.0):
    hover = HoverTool(tooltips = [ ("jobs", "@top"), ("bin", "[@left, @right]") ], point_policy = "snap_to_data")
    TOOLS = ["pan,wheel_zoom,box_zoom,reset,save,box_select", hover]
    p1 = figure(title = value,
                toolbar_location = None, plot_height = 400, plot_width = 600, y_axis_type = "log", tools = TOOLS)
    p1.xaxis.axis_label = units
    p1.yaxis.axis_label = "# Jobs"
    job_list = job_list.filter(**{value + "__isnull" : False})
    values = array(job_list.values_list(value, flat=True))/scale
    if len(values) == 0: return None

    hist, edges = histogram(values,
                            bins = linspace(0, max(values), max(3, 5*log(len(values)))))
    p1.quad(top = hist, bottom = 1, left = edges[:-1], right = edges[1:])    
    return p1

def get_data(pk):
    if cache.has_key(pk):
        data = cache.get(pk)
    else:
        job = Job.objects.get(pk = pk)
        with open(os.path.join(cfg.pickles_dir, 
                               job.date.strftime('%Y-%m-%d'), 
                               str(job.id)), 'rb') as fd:
            try: data = p.load(fd)
            except: data = p.load(fd, encoding = 'latin1') # Python2 compatibility
            cache.set(job.id, data)
    return data

def master_plot(pk):
    data = get_data(pk)
    mp = plots.MasterPlot()
    return components(mp.plot(data))

def heat_map(pk):    
    data = get_data(pk)
    hm = plots.HeatMap()
    return components(hm.plot(data))

def type_plot(pk, typename):    
    data = get_data(pk)
    dp = plots.DevPlot()
    return components(dp.plot(data, typename))

def build_schema(data,name):
    schema = []
    for key,value in data.get_schema(name).items():
        if value.unit:
            schema.append(value.key + ','+value.unit)
        else: schema.append(value.key)
    return schema

metric_names = [
    "avg_cpuusage [#cores]",
    "mem_hwm [GB]", 
    "node_imbalance",
    "time_imbalance",
    "avg_flops_32b [GF]",
    "avg_vector_width_32b [#]",
    "vecpercent_32b [%]",
    "avg_flops_64b [GF]",
    "avg_vector_width_64b [#]",
    "vecpercent_64b [%]",
    "avg_cpi [cyc/ins]", 
    "avg_freq [GHz]", 
    "avg_loads [#/s]", 
    "avg_l1loadhits [#/s]",
    "avg_l2loadhits [#/s]", 
    "avg_llcloadhits [#/s]", 
    "avg_sf_evictrate [#evicts/#rds]", 
    "max_sf_evictrate [#evicts/#rds]", 
    "avg_mbw [GB/s]", 
    "avg_page_hitrate [hits/cas]", 
    "avg_mcdrambw [GB/s]",
    "avg_fabricbw [MB/s]",
    "max_fabricbw [MB/s]",
    "avg_packetsize [MB]",
    "max_packetrate [#/s]", 
    "avg_ethbw [MB/s]",  
    "max_mds [#/s]",
    "avg_lnetmsgs [#/s]", 
    "avg_lnetbw [MB/s]", 
    "max_lnetbw [MB/s]",
    "avg_mdcreqs [#/s]", 
    "avg_mdcwait [us]", 
    "avg_oscreqs [#/s]",
    "avg_oscwait [us]",
    "avg_openclose [#/s]", 
    "avg_blockbw [MB/s]",
    "max_load15 [cores]"
]

class JobDetailView(DetailView):
    model = Job
    def get_context_data(self, **kwargs):
        context = super(JobDetailView, self).get_context_data(**kwargs)
        job = context['job']
        data_host_list = []
        try:
            data = get_data(job.id)
            # Prepare metrics        
            metric_dict = {}
            for name in metric_names:
                val = getattr(job, name.split(' ')[0])
                if val: metric_dict[name] = val
                context['metric_dict'] = metric_dict                
            # Prepare process names
            proc_list = []
            for host_name, host in data.hosts.items():
                if "proc" in host.stats:
                    for proc_pid, val in host.stats['proc'].items():
                        if val[0][0]:
                            try: 
                                proc = proc_pid.split('/')[0]
                            except:
                                proc = proc_pid
                            proc_list += [proc]
                            proc_list = list(set(proc_list))
                            context['proc_list'] = proc_list
            # Prepare FS IO 
            fsio_dict = {}
            schema = data.get_schema('llite')
            rd_idx = schema['read_bytes'].index
            wr_idx = schema['write_bytes'].index
            for host_name, host in data.hosts.items():
                for device, value in host.stats['llite'].items():
                    fsio_dict.setdefault(device, [0.0, 0.0])
                    fsio_dict[device][0] += value[-1, rd_idx]/(1024*1024) 
                    fsio_dict[device][1] += value[-1, wr_idx]/(1024*1024) 
                    context['fsio'] = fsio_dict

            # Prepare device type list
            type_list = []        
            host0 = list(data.hosts.values())[0]
            for type_name, type in host0.stats.items():
                schema = ' '.join(build_schema(data,type_name))
                type_list.append( (type_name, schema[0:200]) )
                type_list = sorted(type_list, key = lambda type_name: type_name[0])
                context['type_list'] = type_list
            data_host_list = data.hosts.keys()
            """
            script, div = sys_plot(job.id)
            context["script"] = script
            context["div"]    = div
            """

            script, div = master_plot(job.id)
            context["mscript"] = script
            context["mdiv"]    = div

            """
            script, div = heat_map(job.id)
            context["hscript"] = script
            context["hdiv"]    = div
            """
        except:
            print("data missing for ", job.id)

        acct_host_list = job.host_set.all().values_list('name', flat=True).distinct()
        hosts_missing = set(acct_host_list) - set(data_host_list)
        if len(hosts_missing):
            job.status += " " + str(len(hosts_missing)) + " hosts' data missing: "
            for h in hosts_missing:
                job.status += h + " "
        context['host_list'] = acct_host_list

        ### Specific to Stampede2 Splunk 
        urlstring="https://scribe.tacc.utexas.edu:8000/en-US/app/search/search?q=search%20"
        hoststring=urlstring+"%20host%3D"+acct_host_list[0]+".frontera.tacc.utexas.edu"
        serverstring=urlstring+"%20mds*%20OR%20%20oss*"
        for host in acct_host_list[1:]:
            hoststring+="%20OR%20%20host%3D"+host+"*"

        hoststring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
        serverstring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
        context['client_url'] = hoststring
        context['server_url'] = serverstring
        ###
        return context

def type_detail(request, pk, type_name):
    data = get_data(pk)

    schema = build_schema(data,type_name)
    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []

    for t in range(len(raw_stats)):
        temp = []
        times = data.times-data.times[0]
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t, event])
        stats.append((times[t],temp))
        
    script, div = type_plot(pk, type_name)
    return render(request, "machine/type_detail.html",
                  {"type_name" : type_name, "jobid" : pk, 
                   "stats_data" : stats, "schema" : schema,
                   "tscript" : script, "tdiv" : div})

def proc_detail(request, pk, proc_name):

    data = get_data(pk)
    
    host_map = {}
    schema = data.get_schema('proc')
    vmp_idx = schema['VmPeak'].index
    hwm_idx = schema['VmHWM'].index
    hwm_unit = "gB"
    thr_idx = schema['Threads'].index

    for host_name, host in data.hosts.items():
        for proc_pid, val in host.stats['proc'].items():

            host_map.setdefault(host_name, {})
            proc_, pid, cpu_aff, mem_aff = proc_pid.split('/') 

            if  proc_ == proc_name:
                host_map[host_name][proc_+'/'+pid] = [ val[-1][vmp_idx]/2**20, val[-1][hwm_idx]/2**20, cpu_aff, val[-1][thr_idx] ]

    return render(request, "machine/proc_detail.html",
                  {"proc_name" : proc_name, "jobid" : pk, 
                   "host_map" : host_map, "hwm_unit" : hwm_unit})
