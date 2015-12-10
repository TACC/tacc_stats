from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.views.generic import DetailView, ListView
from django.db.models import Q

import os,sys,pwd
from tacc_stats.analysis import exam
from tacc_stats.site.machine.models import Job, Host, Libraries, TestInfo
from tacc_stats.site.xalt.models import run, join_run_object, lib
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

def update_comp_info(thresholds = None):
    
    schema_map = {'HighCPI' : ['cpi','>',1.5], 
                  'HighCPLD' : ['cpld','>',1.5], 
                  'Load_L1Hits' : ['Load_L1Hits','>',1.5], 
                  'Load_L2Hits' : ['Load_L2Hits','>',1.5], 
                  'Load_LLCHits' : ['Load_LLCHits','>',1.5], 
                  'MemBw' : ['mbw', '<', 1.0 ],
                  'Catastrophe' : ['cat', '<',0.01] ,
                  'MemUsage' : ['mem','>',31], 
                  'PacketRate' : ['packetrate','>',0], 
                  'PacketSize' : ['packetsize','>',0],
                  'Idle' : ['idle','>',0.99],
                  'LowFLOPS' : ['flops','<',10],
                  'VecPercent' : ['VecPercent','<',0.05],
                  'GigEBW' : ['GigEBW','>',1e7],
                  'CPU_Usage' : ['CPU_Usage','<',800],
                  'MIC_Usage' : ['MIC_Usage','>',0.0],
                  'Load_All' : ['Load_All','<',1e7],
                  'MetaDataRate' : ['MetaDataRate','>',10000],
                  'InternodeIBAveBW' : ['InternodeIBAveBW', '>', 10000],
                  'InternodeIBMaxBW' : ['InternodeIBMaxBW', '>', 10000],
                  'LnetAveBW'  : ['LnetAveBW', '>', 10000],
                  'LnetMaxBW'  : ['LnetMaxBW', '>', 10000],
                  'MDCReqs'  : ['MDCReqs', '>', 10000],
                  'OSCReqs'  : ['OSCReqs', '>', 10000],
                  'OSCWait'  : ['OSCWait', '>', 10000],
                  'MDCWait'  : ['MDCWait', '>', 10000],
                  'LLiteOpenClose'  : ['LLiteOpenClose', '>', 10000],
                  }
    if thresholds:
        for key,val in thresholds.iteritems():
            schema_map[key][1:3] = val

    for name in schema_map:
        if TestInfo.objects.filter(test_name = name).exists():
            TestInfo.objects.filter(test_name = name).delete()

        obj = TestInfo(test_name = name, 
                       field_name = schema_map[name][0], 
                       comparator = schema_map[name][1], 
                       threshold = schema_map[name][2])
        obj.save()

def update(date,rerun=False):

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
                if rerun: pass
                elif Job.objects.filter(id = pickle_file).exists(): 
                    continue                
            except:
                print pickle_file,"doesn't look like a pickled job"
                continue

            try:
                pickle_path = os.path.join(root,str(pickle_file))
                with open(pickle_path, 'rb') as f:
                    data = np.load(f)
                    json = data.acct
                    hosts = data.hosts.keys()
                del json['yesno']
                utc_start = datetime.utcfromtimestamp(
                    json['start_time']).replace(tzinfo=pytz.utc)
                utc_end = datetime.utcfromtimestamp(
                    json['end_time']).replace(tzinfo=pytz.utc)
                json['run_time'] = json['end_time'] - json['start_time']

                if json.has_key('unknown'):
                    json['requested_time'] = json['unknown']*60
                    del json['unknown']
                else: json['requested_time'] = json['requested_time']*60

                json['start_epoch'] = json['start_time']
                json['end_epoch'] = json['end_time']
                json['start_time'] = utc_start.astimezone(tz)
                json['end_time'] =  utc_end.astimezone(tz)
                json['date'] = json['end_time'].date()
                json['name'] = json['name'][0:128]
                json['wayness'] = json['cores']/json['nodes']

                try: json['user']=pwd.getpwuid(int(json['uid']))[0]
                except: json['user']='unknown'
                
                ### If xalt is available add data to the DB 
                xd = None
                try:
                    xd = run.objects.using('xalt').filter(job_id = json['id'])[0]
                    json['user']    = xd.user
                    json['exe']     = xd.exec_path.split('/')[-1][0:128]
                    json['exec_path'] = xd.exec_path
                    json['cwd']     = xd.cwd[0:128]
                    json['threads'] = xd.num_threads
                except: xd = False 
                    
                obj, created = Job.objects.update_or_create(**json)
                for host_name in hosts:
                    h = Host(name=host_name)
                    h.save()
                    h.jobs.add(obj)

                if xd:
                    for join in join_run_object.objects.using('xalt').filter(run_id = xd.run_id):
                        try:
                            object_path = lib.objects.using('xalt').get(obj_id = join.obj_id).object_path
                            module_name = lib.objects.using('xalt').get(obj_id = join.obj_id).module_name
                            if not module_name: module_name = 'none'
                            library = Libraries(object_path = object_path, module_name = module_name)
                            library.save()
                            library.jobs.add(obj)
                        except: pass

            except: 
                print pickle_file,'failed'
                print traceback.format_exc()
                print date
            print "Percentage Completed =",100*float(ctr)/num_files

def update_metric_fields(date,rerun=False):
    update_comp_info()
    aud = exam.Auditor(processes=4)
    
    aud.stage(exam.GigEBW, ignore_qs=[], min_time = 0)
    aud.stage(exam.HighCPI, ignore_qs=[], min_time = 0)
    aud.stage(exam.HighCPLD, ignore_qs=[], min_time = 0)
    aud.stage(exam.Load_L1Hits, ignore_qs=[], min_time = 0)
    aud.stage(exam.Load_L2Hits, ignore_qs=[], min_time = 0)
    aud.stage(exam.Load_LLCHits, ignore_qs=[], min_time = 0)
    aud.stage(exam.MemBw, ignore_qs=[], min_time = 0)
    aud.stage(exam.Catastrophe, ignore_qs=[], min_time = 0)
    aud.stage(exam.MemUsage, ignore_qs=[], min_time = 0)
    aud.stage(exam.PacketRate, ignore_qs=[], min_time = 0)
    aud.stage(exam.PacketSize, ignore_qs=[], min_time = 0)
    aud.stage(exam.Idle, ignore_qs=[], min_time = 0)
    aud.stage(exam.LowFLOPS, ignore_qs=[], min_time = 0)
    aud.stage(exam.VecPercent, ignore_qs=[], min_time = 0)
    aud.stage(exam.CPU_Usage, ignore_qs = [], min_time = 0)
    aud.stage(exam.MIC_Usage, ignore_qs = [], min_time = 0)
    aud.stage(exam.Load_All, ignore_qs = [], min_time = 0)
    aud.stage(exam.MetaDataRate, ignore_qs = [], min_time = 0)
    aud.stage(exam.LnetAveBW, ignore_qs=[], min_time = 0)
    aud.stage(exam.LnetMaxBW, ignore_qs=[], min_time = 0)
    aud.stage(exam.InternodeIBAveBW, ignore_qs=[], min_time = 0)
    aud.stage(exam.InternodeIBMaxBW, ignore_qs=[], min_time = 0)
    aud.stage(exam.MDCReqs, ignore_qs=[], min_time = 0)
    aud.stage(exam.MDCWait, ignore_qs=[], min_time = 0)
    aud.stage(exam.OSCReqs, ignore_qs=[], min_time = 0)
    aud.stage(exam.OSCWait, ignore_qs=[], min_time = 0)
    aud.stage(exam.LLiteOpenClose, ignore_qs=[], min_time = 0)

    print 'Run the following tests for:',date
    for name, test in aud.measures.iteritems():
        print name
        obj = TestInfo.objects.get(test_name = name)
        print obj.field_name,obj.threshold,obj.comparator

    jobs_list = Job.objects.filter(date = date).exclude(run_time__lt = 0)

    # Use mem to see if job was tested.  It will always exist
    if not rerun:
        jobs_list = jobs_list.filter(Load_L1Hits = None)
    
    paths = []
    for job in jobs_list:
        paths.append(os.path.join(cfg.pickles_dir,
                                  job.date.strftime('%Y-%m-%d'),
                                  str(job.id)))
        
    num_jobs = jobs_list.count()
    print '# Jobs to be tested:',num_jobs
    if num_jobs == 0 : return

    aud.run(paths)
    print 'finished computing metrics'

    for name, results in aud.metrics.iteritems():
        obj = TestInfo.objects.get(test_name = name)
        print name,len(results.keys())
        for jobid, result in results.iteritems():            
            try:
                jobs_list.filter(id = jobid).update(**{ obj.field_name : result })
            except:
                pass

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

    fig = Figure(figsize=(17,5))
    ax=fig.add_subplot(1,1,1)
    fig.tight_layout()
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


def dates(request, error = False):
    month_dict ={}
    dates = Job.objects.dates('date','day')
    for date in dates:
        y,m,d = date.strftime('%Y-%m-%d').split('-')
        key = y+'-'+m
        month_dict.setdefault(key, [])
        month_dict[key].append((y+'-'+m+'-'+d, d))
        
    field = {}
    field["machine_name"] = cfg.host_name_ext

    field['date_list'] = sorted(month_dict.iteritems())[::-1]
    field['error'] = error
    return render_to_response("machine/search.html", field)

def search(request):

    if 'jobid' in request.GET:
        try:
            job = Job.objects.get(id = request.GET['jobid'])
            return HttpResponseRedirect("/machine/job/"+str(job.id)+"/")
        except: pass
    try:
        fields = request.GET.dict()
        new_fields = {k:v for k,v in fields.items() if v}
        fields = new_fields

        if 'opt_field0' in fields.keys() and 'value0' in fields.keys():
            fields[fields['opt_field0']] = fields['value0']
            del fields['opt_field0'], fields['value0']
        if 'opt_field1' in fields.keys() and 'value1' in fields.keys():
            fields[fields['opt_field1']] = fields['value1']
            del fields['opt_field1'], fields['value1']
        if 'opt_field2' in fields.keys() and 'value2' in fields.keys():
            fields[fields['opt_field2']] = fields['value2']
            del fields['opt_field2'], fields['value2']

        print 'search', fields
        return index(request, **fields)
    except: pass

    return dates(request, error = True)
    

def index(request, **field):


    print 'index',field
    name = ''
    for key, val in field.iteritems():
        name += '['+key+'='+val+']-'


    #if 'run_time__gte' in field: pass
    #else: field['run_time__gte'] = 60

    order_key = '-id'
    if 'order_key' in field: 
        order_key = field['order_key']
        del field['order_key']
        
    if field.has_key('date'): 
        date = field['date'].split('-')
        if len(date) == 2:
            field['date__year'] = date[0]
            field['date__month'] = date[1]
            del field['date']

    job_list = Job.objects.filter(**field).order_by(order_key)

    field['name'] = name + 'search'
    field['histograms'] = hist_summary(job_list)
    
    field['job_list'] = job_list
    field['nj'] = job_list.count()

    # Computed Metrics
    field['cat_job_list']  = job_list.filter(Q(cat__lte = 0.001) | Q(cat__gte = 1000)).exclude(cat = float('nan'))
    
    completed_list = job_list.exclude(status__in=['CANCELLED','FAILED']).order_by('-id')
    if len(completed_list) > 0:
        try: 
            field['md_job_list'] = job_list.order_by('-MetaDataRate')[0:10]
        except:
            field['md_job_list'] = job_list.order_by('-MetaDataRate')
        field['idle_job_list'] = completed_list.filter(idle__gte = 0.99)
        field['mem_job_list'] = completed_list.filter(mem__lte = 30, queue = 'largemem')

        field['cpi_thresh'] = 1.5
        field['cpi_job_list']  = completed_list.exclude(cpi = float('nan')).filter(cpi__gte = field['cpi_thresh'])
        field['cpi_per'] = 100*field['cpi_job_list'].count()/float(completed_list.count())

        field['gigebw_thresh'] = 2**20
        field['gigebw_job_list']  = completed_list.exclude(GigEBW = float('nan')).filter(GigEBW__gte = field['gigebw_thresh'])
        try:
            field['md_job_list'] = list_to_dict(field['md_job_list'],'MetaDataRate')
        except: 
            field['md_job_list'] = None
        field['idle_job_list'] = list_to_dict(field['idle_job_list'],'idle')
        field['cat_job_list'] = list_to_dict(field['cat_job_list'],'cat')
        field['cpi_job_list'] = list_to_dict(field['cpi_job_list'],'cpi')
        field['mem_job_list'] = list_to_dict(field['mem_job_list'],'mem')
        field['gigebw_job_list'] = list_to_dict(field['gigebw_job_list'],'GigEBW')

    return render_to_response("machine/index.html", field)

def list_to_dict(job_list,metric):
    job_dict={}
    for job in job_list:
        job_dict.setdefault(job.user,[]).append((job.id,round(job.__dict__[metric],3)))
    return job_dict
    
def hist_summary(job_list):

    fig = Figure(figsize=(16,6))

    # Runtimes
    jobs = np.array(job_list.values_list('run_time',flat=True))/3600.
    ax = fig.add_subplot(221)
    bins = np.linspace(0, max(jobs), max(5, 5*np.log(len(jobs))))
    ax.hist(jobs, bins = bins, log=True, color='#bf0a30')
    ax.set_ylabel('# of jobs')
    ax.set_xlabel('hrs')
    ax.set_title('Runtime')

    # Nodes
    jobs =  np.array(job_list.values_list('nodes',flat=True))
    ax = fig.add_subplot(222)
    bins = np.linspace(0, max(jobs), max(5, 5*np.log(len(jobs))))
    ax.hist(jobs, bins = bins, log=True, color='#bf0a30')
    ax.set_title('Size')
    ax.set_xlabel('nodes')

    # Queue Wait Time
    jobs =  (np.array(job_list.values_list('start_epoch',flat=True))-np.array(job_list.values_list('queue_time',flat=True)))/3600.
    ax = fig.add_subplot(223)
    bins = np.linspace(0, max(jobs), max(5, 5*np.log(len(jobs))))
    ax.hist(jobs, bins = bins, log=True, color='#bf0a30')
    ax.set_ylabel('# of jobs')
    ax.set_title('Queue Wait Time')
    ax.set_xlabel('hrs')
    #jobs =  np.array(job_list.filter(status = "FAILED").values_list('nodes',flat=True))
    jobs =  np.array(job_list.values_list('MetaDataRate',flat=True))
    ax = fig.add_subplot(224)
    try:
        bins = np.linspace(0, max(jobs), max(5, 5*np.log(len(jobs))))
        ax.hist(jobs, bins = bins, log=True, color='#bf0a30')
    except: pass
    ax.set_title('Metadata Reqs')
    ax.set_xlabel('<reqs>/s')


    fig.subplots_adjust(hspace=0.5)      
    canvas = FigureCanvas(fig)
    
    import StringIO,base64,urllib
    imgdata = StringIO.StringIO()
    fig.savefig(imgdata, format='png')
    imgdata.seek(0)
    response = "data:image/png;base64,%s" % base64.b64encode(imgdata.buf)

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
    mp = plots.MasterPlot()
    mp.plot(pk,job_data=data)
    return figure_to_response(mp)

def heat_map(request, pk):    
    data = get_data(pk)
    hm = plots.HeatMap(k1={'intel_snb' : ['intel_snb','intel_snb'],
                           'intel_hsw' : ['intel_hsw','intel_hsw'],
                           'intel_ivb' : ['intel_ivb','intel_ivb'],
                           'intel_pmc3' : ['intel_pmc3','intel_pmc3']
                           },
                       k2={'intel_snb' : ['CLOCKS_UNHALTED_REF', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_ivb' : ['CLOCKS_UNHALTED_REF', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_hsw' : ['CLOCKS_UNHALTED_REF', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_pmc3' : ['CLOCKS_UNHALTED_REF', 
                                           'INSTRUCTIONS_RETIRED']                           
                           },
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

        import operator
        comp = {'>': operator.gt, '>=': operator.ge,
                '<': operator.le, '<=': operator.le,
                '==': operator.eq}
        
        
        print ">>>>>>>>>>>>>>>>>>>>>>>>"
        testinfo_dict = {}
        for obj in TestInfo.objects.all():
            print obj.test_name,
            test_type = getattr(sys.modules[exam.__name__],obj.test_name)
            test = test_type(min_time=0,ignore_qs=[])
            try: 
                metric = test.test(job.path,data)
                print metric
                if not metric: continue            
                setattr(job,obj.field_name,metric)
                result = comp[obj.comparator](metric, obj.threshold)
                if result: string = 'Failed'
                else: string = 'Passed'
                testinfo_dict[obj.test_name] = (metric,obj.threshold,string)
            except: continue
        context['testinfo_dict'] = testinfo_dict

        proc_list = []
        type_list = []
        host_list = []

        for host_name, host in data.hosts.iteritems():
            if host.stats.has_key('proc'):
                for proc_pid,val in host.stats['proc'].iteritems():
                    if job.uid == val[0][0]:

                        try: 
                            proc = proc_pid.split('/')[0]
                        except:
                            proc = proc_pid

                        proc_list += [proc]
                proc_list = list(set(proc_list))
            host_list.append(host_name)

        if len(host_list) != job.nodes:
            job.status = str(job.nodes-len(host_list))+"_NODES_MISSING"
        host0=data.hosts.values()[0]
        for type_name, type in host0.stats.iteritems():
            schema = ' '.join(build_schema(data,type_name))
            type_list.append( (type_name, schema[0:200]) )

        type_list = sorted(type_list, key = lambda type_name: type_name[0])

        context['proc_list'] = proc_list
        context['host_list'] = host_list
        context['type_list'] = type_list

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

    k1 = {'intel_snb' : [type_name]*len(schema),
          'intel_hsw' : [type_name]*len(schema),
          'intel_ivb' : [type_name]*len(schema),
          'intel_pmc3' : [type_name]*len(schema)
          }
    k2 = {'intel_snb': schema,
          'intel_hsw': schema,
          'intel_ivb' : schema,
          'intel_pmc3': schema
          }

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

    return render_to_response("machine/type_detail.html",{"type_name" : type_name, "jobid" : pk, "stats_data" : stats, "schema" : schema})

def proc_detail(request, pk, proc_name):

    data = get_data(pk)
    
    host_map = {}
    schema = data.get_schema('proc')
    hwm_idx = schema['VmHWM'].index
    hwm_unit = "gB"#schema['VmHWM'].unit
    aff_idx = schema['Cpus_allowed_list'].index
    thr_idx = schema['Threads'].index

    for host_name, host in data.hosts.iteritems():

        for proc_pid, val in host.stats['proc'].iteritems():
            host_map.setdefault(host_name, {})
            try:
                proc_ = proc_pid.split('/')[0] 
            except: 
                proc_ = proc_pid
            if  proc_ == proc_name:
                host_map[host_name][proc_pid] = [ val[-1][hwm_idx]/2**20, format(int(val[-1][aff_idx]),'#018b')[2:], val[-1][thr_idx] ]

    return render_to_response("machine/proc_detail.html",{"proc_name" : proc_name, "jobid" : pk, "host_map" : host_map, "hwm_unit" : hwm_unit})
