from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.views.generic import DetailView, ListView
from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.core.cache import cache 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

import logging

import os,sys,pwd,inspect
import cPickle as pickle 
import requests

from tacc_stats.analysis import exam
from tacc_stats.site.machine.models import Job, Host, Libraries, TestInfo
from tacc_stats.site.xalt.models import run, join_run_object, lib
import tacc_stats.cfg as cfg
import tacc_stats.analysis.plot as plots

from datetime import datetime, timedelta

import numpy as np

from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.plotting import figure
from bokeh.models import HoverTool

from agavepy.agave import Agave

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
    if not request.session["is_staff"]:
        job_objects = job_objects.filter(user = request.session["username"])

    job = job_objects.get(id=pk)
    jh = job.host_set.all().values_list('name', flat=True).distinct()

    hover = HoverTool(tooltips = [ ("host", "@x-@y") ])
    plot = figure(title = "System Plot", tools = [hover], 
                  toolbar_location = None,
                  x_range = racks, y_range = nodes, 
                  plot_height = 800, plot_width = 1000)
    """
    import time
    start = time.time()
    ctr = 0
    for rack in racks:
        for node in nodes:
            name = str(rack)+'-'+str(node)
            if name in jh: 
                sys_color[ctr] = ["#bf0a30"] 
            ctr+=1
    print "sys",time.time()-start
    plot.xaxis.major_label_orientation = "vertical"
    plot.rect(xrack, yrack, 
              color = sys_color, width = 1, height = 1)    
    """
    return components(plot)


logging.basicConfig()
logger = logging.getLogger('logger')

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

    tenant_base_url = settings.AGAVE_BASE_URL
    client_key = settings.AGAVE_CLIENT_KEY
    client_secret = settings.AGAVE_CLIENT_SECRET
    redirect_uri = 'http://{}{}'.format(request.get_host(), reverse('agave_oauth_callback'))

    body = {
        'token': request.session['access_token'],
        'token_type_hint': 'access_token'
    }

    response = requests.post('%s/revoke' % tenant_base_url, 
        data=body, 
        auth=(client_key, client_secret))
    request.session.flush()
    return HttpResponseRedirect("/")
    
def login_prompt(request):
    if check_for_tokens(request):
        return HttpResponseRedirect("/")
    return render(request, "machine/login_prompt.html", {"logged_in": False})

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

        logger.error(token_data.keys())

        headers = {'Authorization': 'Bearer %s' % token_data['access_token']}
        user_response = requests.get('%s/profiles/v2/me?pretty=true' %tenant_base_url, headers=headers)
        user_data = user_response.json()

        request.session['access_token'] = token_data['access_token']
        request.session['refresh_token'] = token_data['refresh_token']
        request.session['username'] = user_data['result']['username']
        logger.error(request.session['access_token'])
        # For now we determine whether a user is staff by seeing if hey have an @tacc.utexas.edu email.
        request.session['email'] = user_data['result']['email']
        request.session['is_staff'] = user_data['result']['email'].split('@')[-1] == 'tacc.utexas.edu'
        #request.session['is_staff'] = False
        return HttpResponseRedirect("/")

def dates(request, error = False):

    if not check_for_tokens(request):
        return HttpResponseRedirect("/login_prompt")

    month_dict ={}
    date_list = Job.objects.exclude(date = None).exclude(date__lt = datetime.today() - timedelta(days = 90)).values_list('date',flat=True).distinct()
    if not request.session["is_staff"]:
        date_list = date_list.filter(user=request.session["username"])

    for date in sorted(date_list):
        y,m,d = date.strftime('%Y-%m-%d').split('-')
        key = y+'-'+m
        month_dict.setdefault(key, [])
        month_dict[key].append((y+'-'+m+'-'+d, d))

    field = {}
    field["machine_name"] = cfg.host_name_ext

    field['md_job_list'] = Job.objects.filter(date__gt = datetime.today() - timedelta(days = 5)).exclude(LLiteOpenClose__isnull = True ).annotate(io = ExpressionWrapper(F('LLiteOpenClose')*F('nodes'), output_field = FloatField())).order_by('-io')
    if not request.session["is_staff"]:
        field['md_job_list'] = field['md_job_list'].filter(user=request.session["username"])

    try:
        field['md_job_list'] = field['md_job_list'][0:10]
    except: pass    
    field['md_job_list'] = list_to_dict(field['md_job_list'],'io')

    field['date_list'] = sorted(month_dict.iteritems())[::-1]
    field['error'] = error
    field['username'] = request.session['username']
    field['is_staff'] = request.session['is_staff']
    field['email'] = request.session['email']
    field['logged_in'] = True
    return render(request, "machine/search.html", field)

def search(request):

    if 'jobid' in request.GET:
        try:
            job_objects = Job.objects
            if not request.session["is_staff"]:
                job_objects = job_objects.filter(user = request.session["username"])
            job = job_objects.get(id = request.GET['jobid'])

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

    
    job_list = Job.objects.filter(**fields).distinct().order_by(order_key)
    if not request.session["is_staff"]:
        job_list = job_list.filter(user = request.session["username"])

    fields['name'] =  'Query [fields=values] ' + name.rstrip('-')    

    paginator = Paginator(job_list,100)
    page = request.GET.get('page')
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)

    job_list = job_list.annotate(queue_wait = F("start_epoch") - F("queue_time"))
    fields["script"], fields["div"] = components(gridplot(job_hist(job_list, "run_time", "Hours", 
                                                                   scale = 3600),
                                                          job_hist(job_list, "nodes", "# Nodes"),
                                                          job_hist(job_list, "queue_wait", "Hours", 
                                                                   scale = 3600),
                                                          job_hist(job_list, "LLiteOpenClose", "iops"), 
                                                          ncols = 2, toolbar_options = {"logo" : None},
                                                          plot_width = 400, plot_height = 200)
                                             )
    
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

    fields['logged_in'] = True
    if '?' in request.get_full_path():
        fields['current_path'] = request.get_full_path()
    return render(request, "machine/index.html", fields)

def list_to_dict(job_list,metric):
    job_dict={}
    for job in job_list:
        job_dict.setdefault(job.user,[]).append((job.id,round(job.__dict__[metric],3)))
    return job_dict
    
def job_hist(job_list, value, units, scale = 1.0):
    hover = HoverTool(tooltips = [ ("jobs", "@top"), ("bin", "[@left, @right]") ], point_policy = "snap_to_data")
    TOOLS = ["pan,wheel_zoom,box_zoom,reset,save,box_select", hover]
    p1 = figure(title = value, logo = None,
                toolbar_location = None, plot_height = 400, plot_width = 600, y_axis_type = "log", tools = TOOLS)
    p1.xaxis.axis_label = units
    p1.yaxis.axis_label = "# Jobs"
    job_list = job_list.filter(**{value + "__isnull" : False})
    values = np.array(job_list.values_list(value, flat=True))/scale
    if len(values) == 0: return None

    hist, edges = np.histogram(values,
                               bins = np.linspace(0, max(values), max(3, 5*np.log(len(values)))))
    p1.quad(top = hist, bottom = 1, left = edges[:-1], right = edges[1:])    
    return p1

def get_data(request, pk):
    if cache.has_key(pk):
        data = cache.get(pk)
    else:

        job_objects = Job.objects

        #.filter(user=request.session["username"])
        if not request.session["is_staff"]:
            job_objects = job_objects.filter(user=request.session["username"])
        
        try:
            job = job_objects.get(pk=pk)
        except Job.DoesNotExist:
            return None

        with open(os.path.join(cfg.pickles_dir,job.date.strftime('%Y-%m-%d'),str(job.id)),'rb') as f:
            data = pickle.load(f)
            cache.set(job.id, data)
    return data

def master_plot(request, pk):
    data = get_data(request, pk)
    mp = plots.MasterPlot()
    return components(mp.plot(data))

def heat_map(request, pk):    
    data = get_data(request, pk)
    hm = plots.HeatMap()
    return components(hm.plot(data))

def type_plot(request, pk, typename):    
    data = get_data(request, pk)
    dp = plots.DevPlot()
    return components(dp.plot(data, typename))

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
        data = get_data(self.request, job.id)

        if not data:
            return None

        testinfo_dict = {}
        for obj in TestInfo.objects.all():
            test_type = getattr(sys.modules[exam.__name__],obj.test_name)
            test = test_type(min_time=0,ignore_qs=[])
            try: 
                metric = test.test(os.path.join(cfg.pickles_dir, 
                                                job.date.strftime('%Y-%m-%d'),
                                                str(job.id)), data)
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
                    if val[0][0]:

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

        ### Specific to Stampede2 Splunk 
        urlstring="https://scribe.tacc.utexas.edu:8000/en-US/app/search/search?q=search%20"
        hoststring=urlstring+"%20host%3D"+host_list[0]+".stampede2.tacc.utexas.edu"
        serverstring=urlstring+"%20mds*%20OR%20%20oss*"
        for host in host_list[1:]:
            hoststring+="%20OR%20%20host%3D"+host+"*"

        hoststring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
        serverstring+="&earliest="+str(job.start_epoch)+"&latest="+str(job.end_epoch)+"&display.prefs.events.count=50"
        context['client_url'] = hoststring
        context['server_url'] = serverstring
        ###
        """
        script, div = sys_plot(self.request, job.id)
        context["script"] = script
        context["div"]    = div
        """
        
        script, div = master_plot(self.request, job.id)
        context["mscript"] = script
        context["mdiv"]    = div
        
        """
        script, div = heat_map(self.request, job.id)
        context["hscript"] = script
        context["hdiv"]    = div
        """
        context['logged_in'] = True
        return context

def type_detail(request, pk, type_name):
    data = get_data(request, pk)

    schema = build_schema(data,type_name)
    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []

    for t in range(len(raw_stats)):
        temp = []
        times = data.times-data.times[0]
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t, event])
        stats.append((times[t],temp))
        
    script, div = type_plot(request, pk, type_name)

    return render(request, "machine/type_detail.html",
                  {"type_name" : type_name, "jobid" : pk, 
                   "stats_data" : stats, "schema" : schema,
                   "tscript" : script, "tdiv" : div, "logged_in" : True})

def proc_detail(request, pk, proc_name):

    data = get_data(request, pk)
    
    host_map = {}
    schema = data.get_schema('proc')
    hwm_idx = schema['VmHWM'].index
    aff_idx = schema['Cpus_allowed_list'].index
    hwm_unit = "gB"
    thr_idx = schema['Threads'].index
                                                    
    for host_name, host in data.hosts.iteritems():
        for proc_pid, val in host.stats['proc'].iteritems():
            host_map.setdefault(host_name, {})
            try:
                proc_, pid, cpu_aff, mem_aff = proc_pid.split('/') 
                if  proc_ == proc_name:
                    host_map[host_name][proc_+'/'+pid] = [ val[-1][hwm_idx]/2**20, 
                                                           cpu_aff, val[-1][thr_idx] ]
            except:
                proc_ = proc_pid.split('/')[0]
                if  proc_ == proc_name:
                    host_map[host_name][proc_pid] = [ val[-1][hwm_idx]/2**20, 
                                                      format(int(val[-1][aff_idx]), '#018b')[2:], 
                                                      val[-1][thr_idx] ]

    return render(request, "machine/proc_detail.html",
                  {"proc_name" : proc_name, "jobid" : pk, 
                   "host_map" : host_map, "hwm_unit" : hwm_unit})
