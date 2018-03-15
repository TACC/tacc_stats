from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response, render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import DetailView, ListView
from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.core.cache import cache 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings

import os,sys,pwd,inspect
import cPickle as pickle 
import operator
import json, requests

from tacc_stats.analysis import exam
from tacc_stats.site.machine.models import Job, Host, Libraries, TestInfo
from tacc_stats.site.xalt.models import run, join_run_object, lib
import tacc_stats.cfg as cfg
import tacc_stats.analysis.plot as plots

from datetime import datetime, timedelta

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from agavepy.agave import Agave

# Agave authentication functions (shamelessly stolen from:
# https://bitbucket.org/jstubbs/ipt-web/src/8b637b9570dd870eef459b953a69c4d18e181c8e/iptweb/iptsite/views.py?at=master&fileviewer=file-view-default#views.py-176)

def get_request():
    """Walk up the stack, return the nearest first argument named "request"."""
    frame = None
    try:
        for f in inspect.stack()[1:]:
            frame = f[0]
            code = frame.f_code
            if code.co_varnames and code.co_varnames[0] == "request":
                request = frame.f_locals['request']
    finally:
        del frame
    return request

def check_for_tokens(request):
    access_token = request.session.get("access_token")
    if access_token:
        return True
    return False

def update_session_tokens(**kwargs):
    """Update the request's session with the latest tokens since the client may have
    automatically refreshed them."""

    request = get_request()
    request.session['access_token'] = kwargs['access_token']
    request.session['refresh_token'] = kwargs['refresh_token']

def get_agave_client(username, password):
    client_key = settings.AGAVE_CLIENT_KEY
    client_secret = settings.AGAVE_CLIENT_SECRET
    base_url = settings.AGAVE_BASE_URL

    if not client_key or not client_secret:
        raise Exception("Missing OAuth client credentials.")
        
    return Agave(api_server=base_url, username=username, password=password, client_name="tacc-stats",
     api_key=client_key, api_secret=client_secret, token_callback=update_session_tokens)
    
# login view with Agave functionality
def login(request):


    if check_for_tokens(request):
        return HttpResponseRedirect('/')

    if request.method=='POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username:
            context = {"error": "Username cannot be blank"}
            return render(request, 'registration/login.html', context, content_type='text/html')
            
        if not password:
            context = {"error": "Password cannot be blank"}
            return render(request, 'registration/login.html', context, content_type='text/html')

        try:
            ag = get_agave_client(username, password)
        except Exception as e:
            context = {"error": "Invalid username or password: {}".format(e)}
            return render(request, 'registration/login.html', context, content_type='text/html')
            
        # at this point the Agave client has been generated.
        access_token = ag.token.token_info['access_token']
        refresh_token = ag.token.token_info['refresh_token']
        token_exp = ag.token.token_info['expires_at']

        request.session['username'] = username
        request.session['access_token'] = access_token
        request.session['refresh_token'] = refresh_token

        return HttpResponseRedirect("/")
    
    elif request.method == 'GET':
        return render(request, 'registration/login.html')

    return render(request, 'registration/login.html')

def logout(request):
    request.session.flush()
    return HttpResponseRedirect("/")

def login_oauth(request):
    tenant_base_url = settings.AGAVE_BASE_URL
    client_key = settings.AGAVE_CLIENT_KEY

    session = request.session
    session['auth_state'] = os.urandom(24).encode('hex')

    redirect_uri = 'http://{}{}'.format(request.get_host(), reverse('agave_oauth_callback'))

    authorization_url = (
        '%s/authorize?client_id=%s&response_type=code&redirect_uri=%s&state=%s' %(
            tenant_base_url,
            client_key,
            redirect_uri,
            session['auth_state']
        )
    )
    return HttpResponseRedirect(authorization_url)


def agave_oauth_callback(request):
    state = request.GET.get('state')

    if request.session['auth_state'] != state:
        return HttpResponseBadRequest('Authorization state failed.')

    if 'code' in request.GET:
        redirect_uri = 'http://{}{}'.format(request.get_host(),
            reverse('agave_oauth_callback'))
        code = request.GET['code']
        tenant_base_url = settings.AGAVE_BASE_URL
        client_key = settings.AGAVE_CLIENT_KEY
        client_secret = settings.AGAVE_CLIENT_SECRET
        redirect_uri = redirect_uri
        body = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }

        response = requests.post('%s/token' % tenant_base_url,
            data=body,
            auth=(client_key, client_secret))
        token_data = response.json()

        headers = {'Authorization': 'Bearer %s' % token_data['access_token']}
        user_response = requests.get('%s/profiles/v2/me?pretty=true' %tenant_base_url, headers=headers)
        user_data = user_response.json()

        request.session['access_token'] = token_data['access_token']
        request.session['refresh_token'] = token_data['refresh_token']
        request.session['username'] = user_data['result']['username']
        request.session['is_staff'] = user_data['result']['email'].split('@')[-1] == 'tacc.utexas.edu'

        return HttpResponseRedirect("/")

def sys_plot(request, pk):

    job = Job.objects.filter(user = request.session["username"]).uget(id=pk)
    hosts = job.host_set.all().values_list('name',flat=True)

    racks = []
    nodes = []
    for host in Host.objects.values_list('name',flat=True).distinct():
        try:
            r,n=host.split('-')
            racks.append(r)
            nodes.append(n)
        except:
            pass
    racks = sorted(set(racks))
    nodes = sorted(set(nodes))

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

    if not check_for_tokens(request):
        return HttpResponseRedirect("/login")

    month_dict ={}
    date_list = Job.objects.filter(user = request.session["username"]).exclude(date = None).exclude(date__lt = datetime.today() - timedelta(days = 90)).values_list('date',flat=True).distinct()

    for date in sorted(date_list):
        y,m,d = date.strftime('%Y-%m-%d').split('-')
        key = y+'-'+m
        month_dict.setdefault(key, [])
        month_dict[key].append((y+'-'+m+'-'+d, d))

    field = {}
    field["machine_name"] = cfg.host_name_ext

    field['md_job_list'] = Job.objects.filter(user = request.session["username"]).filter(date__gt = datetime.today() - timedelta(days = 5)).exclude(LLiteOpenClose__isnull = True ).annotate(io = ExpressionWrapper(F('LLiteOpenClose')*F('nodes'), output_field = FloatField())).order_by('-io')

    try:
        field['md_job_list'] = field['md_job_list'][0:10]
    except: pass    
    field['md_job_list'] = list_to_dict(field['md_job_list'],'io')

    field['date_list'] = sorted(month_dict.iteritems())[::-1]
    field['error'] = error
    field['username'] = request.session['username']
    return render_to_response("machine/search.html", field)

def search(request):

    if 'jobid' in request.GET:
        try:
            job = Job.objects.filter(user = request.session["user"]).get(id = request.GET['jobid'])
            return HttpResponseRediret("/machine/job/"+str(job.id)+"/")
        except: pass
    try:
        return index(request)
    except: pass

    return dates(request, error = True)
    

def index(request, **kwargs):

    fields = request.GET.dict()
    fields = {k:v for k,v in fields.items() if v}
    fields.update(kwargs)

    if 'page' in fields: del fields['page']
    if 'opt_field1' in fields.keys() and 'value1' in fields.keys():
        fields[fields['opt_field1']] = fields['value1']
        del fields['opt_field1'], fields['value1']
    if 'opt_field2' in fields.keys() and 'value2' in fields.keys():
        fields[fields['opt_field2']] = fields['value2']
        del fields['opt_field2'], fields['value2']
    if 'opt_field3' in fields.keys() and 'value3' in fields.keys():
        fields[fields['opt_field3']] = fields['value3']
        del fields['opt_field3'], fields['value3']

    name = ''
    for key, val in fields.iteritems():
        name += key+'='+val+'\n'

    order_key = '-id'
    if 'order_key' in fields: 
        order_key = fields['order_key']
        del fields['order_key']
        
    if fields.has_key('date'): 
        date = fields['date'].split('-')
        if len(date) == 2:
            fields['date__year'] = date[0]
            fields['date__month'] = date[1]
            del fields['date']


    job_list = Job.objects.filter(user = request.session["username"]).filter(**fields).distinct().order_by(order_key)

    fields['name'] =  'Query [fields=values] ' + name.rstrip('-')    

    paginator = Paginator(job_list,100)
    page = request.GET.get('page')
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)

    fields['histograms'] = hist_summary(job_list)
    
    fields['job_list'] = jobs
    fields['nj'] = job_list.count()

    # Computed Metrics
    fields['cat_job_list']  = job_list.filter(Q(cat__lte = 0.001) | Q(cat__gte = 1000)).exclude(cat = float('nan'))
    
    completed_list = job_list.exclude(status__in=['CANCELLED','FAILED']).order_by('-id')
    if len(completed_list) > 0:
        fields['md_job_list'] = job_list.exclude(LLiteOpenClose__isnull = True ).order_by('-LLiteOpenClose')
        try:
            fields['md_job_list'] = fields['md_job_list'][0:10]
        except: pass

        fields['idle_job_list'] = completed_list.filter(idle__gte = 0.99)
        fields['mem_job_list'] = completed_list.filter(mem__lte = 30, queue = 'largemem')

        fields['cpi_thresh'] = 1.5
        fields['cpi_job_list']  = completed_list.exclude(cpi = float('nan')).filter(cpi__gte = fields['cpi_thresh'])
        fields['cpi_per'] = 100*fields['cpi_job_list'].count()/float(completed_list.count())

        fields['gigebw_thresh'] = 2**20
        fields['gigebw_job_list']  = completed_list.exclude(GigEBW = float('nan')).filter(GigEBW__gte = fields['gigebw_thresh'])

        fields['md_job_list'] = list_to_dict(fields['md_job_list'],'LLiteOpenClose')
        fields['idle_job_list'] = list_to_dict(fields['idle_job_list'],'idle')
        fields['cat_job_list'] = list_to_dict(fields['cat_job_list'],'cat')
        fields['cpi_job_list'] = list_to_dict(fields['cpi_job_list'],'cpi')
        fields['mem_job_list'] = list_to_dict(fields['mem_job_list'],'mem')
        fields['gigebw_job_list'] = list_to_dict(fields['gigebw_job_list'],'GigEBW')

    if '?' in request.get_full_path():
        fields['current_path'] = request.get_full_path()
    return render_to_response("machine/index.html", fields)

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

    jobs =  np.array(job_list.filter(LLiteOpenClose__isnull = False).values_list('LLiteOpenClose',flat=True))
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
        job = Job.objects.filter(user = request.session["username"]).get(pk = pk)
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
                           'intel_knl' : ['intel_knl','intel_knl'],
                           'intel_skx' : ['intel_skx','intel_skx'],
                           'intel_pmc3' : ['intel_pmc3','intel_pmc3']
                           },
                       k2={'intel_snb' : ['CLOCKS_UNHALTED_CORE', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_ivb' : ['CLOCKS_UNHALTED_CORE', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_hsw' : ['CLOCKS_UNHALTED_CORE', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_skx' : ['CLOCKS_UNHALTED_CORE', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_knl' : ['CLOCKS_UNHALTED_CORE', 
                                          'INSTRUCTIONS_RETIRED'],
                           'intel_pmc3' : ['CLOCKS_UNHALTED_CORE', 
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
                
        testinfo_dict = {}
        for obj in TestInfo.objects.all():
            test_type = getattr(sys.modules[exam.__name__],obj.test_name)
            test = test_type(min_time=0,ignore_qs=[])
            try: 
                metric = test.test(os.path.join(cfg.pickles_dir, 
                                                job.date.strftime('%Y-%m-%d'),
                                                str(job.id)), data)
                print test,metric
                if not metric or np.isnan(metric) : continue            
                setattr(job,obj.field_name,metric)
                testinfo_dict[obj.test_name] = metric
            except: continue
        context['testinfo_dict'] = testinfo_dict

        proc_list = []
        type_list = []
        host_list = []

        fsio_dict = {}

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
            try:
                if host.stats.has_key('llite'):
                    schema = data.get_schema('llite')
                    rd_idx = schema['read_bytes'].index
                    wr_idx = schema['write_bytes'].index

                    for device, value in host.stats['llite'].iteritems():
                        fsio_dict.setdefault(device, [0.0, 0.0])
                        fsio_dict[device][0] += value[-1, rd_idx] 
                        fsio_dict[device][1] += value[-1, wr_idx]
            except:
                pass
        for key, val in fsio_dict.iteritems():
            val[0] = val[0] * 2.0**(-20)
            val[1] = val[1] * 2.0**(-20)
        context['fsio'] = fsio_dict

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
            hoststring+="%20OR%20%20host%3D"+host+"*"

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
          'intel_knl' : [type_name]*len(schema),
          'intel_skx' : [type_name]*len(schema),
          'intel_pmc3' : [type_name]*len(schema)
          }
    k2 = {'intel_snb': schema,
          'intel_hsw': schema,
          'intel_ivb' : schema,
          'intel_knl' : schema,
          'intel_skx' : schema,
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

    thr_idx = schema['Threads'].index

    for host_name, host in data.hosts.iteritems():

        for proc_pid, val in host.stats['proc'].iteritems():

            host_map.setdefault(host_name, {})
            proc_, pid, cpu_aff, mem_aff = proc_pid.split('/') 

            if  proc_ == proc_name:
                host_map[host_name][proc_+'/'+pid] = [ val[-1][hwm_idx]/2**20, cpu_aff, val[-1][thr_idx] ]

    return render_to_response("machine/proc_detail.html",{"proc_name" : proc_name, "jobid" : pk, "host_map" : host_map, "hwm_unit" : hwm_unit})
