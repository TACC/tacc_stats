from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import DetailView, ListView
from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.core.cache import cache
from django.db.models.functions import Cast 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django import forms

import os,sys,pwd

from tacc_stats.analysis.metrics import metrics
from tacc_stats.analysis.gen import jid_table
from tacc_stats.site.machine.models import job_data, metrics_data
from tacc_stats.site.xalt.models import run, join_run_object, lib
import tacc_stats.cfg as cfg
import tacc_stats.analysis.plot as plots

from datetime import datetime, timedelta

from numpy import array, histogram, log, linspace
from pandas import DataFrame

from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.plotting import figure
from bokeh.models import HoverTool
import time
#try:
#from tacc_stats.site.machine.agave_auth import check_for_tokens
#except:
#pass

import psycopg2
from pandas import DataFrame, read_sql, to_timedelta

CONNECTION = "dbname=ls6_db1 host=localhost user=postgres port=5432"

def home(request, error = False):
    field = {}
    month_dict ={}
    date_list = DataFrame(job_data.objects.values("end_time"))["end_time"].dt.date.drop_duplicates()
    print(date_list)
    
    for date in date_list.sort_values():
        y, m, d = str(date.year), str(date.month), str(date.day)
        month_dict.setdefault(y + '-' + m, [])
        month_dict[y + '-' + m].append((str(date), d))

    field["machine_name"] = cfg.host_name_ext
    field['date_list'] = sorted(month_dict.items())[::-1]
    field['error'] = error

    field['metrics'] = metrics_data.objects.distinct("metric").values("metric", "units")

    field["choice"] = ChoiceForm()
    return render(request, "machine/search.html", field)

def search(request):

    if 'jid' in request.GET:
        try:
            job_objects = job_data.objects            
            job = job_objects.get(jid = request.GET['jid'])
            return HttpResponseRedirect("/machine/job/"+str(job.jid)+"/")
        except: pass
    elif 'host' in request.GET and request.GET["host"]:
        print("try to get host")
        return host_detail(request)
    else:
        #try:
        return index(request)
        #except: pass

    return home(request, error = True)
    

def index(request, **kwargs):

    fields = request.GET.dict()    
    fields = { k:v for k, v in fields.items() if v }
    fields.update(kwargs)
    print(fields)

    ### Filter 
    # Build query and filter on job accounting data
    acct_data = { k:v for k,v in fields.items() if k.split('_', 1)[0] != "metrics" and k != "page" }
    job_list = job_data.objects.filter(**acct_data).order_by('-end_time')

    # Build query and filter iteratively on derived metrics data
    df_fields = []
    metrics = { k.split('_',1)[1]:v for k,v in fields.items() if k.split('_', 1)[0] == "metrics" }
    for key, val in metrics.items():
        name, op = key.split('__')
        mquery = { "metrics_data__metric" : name, "metrics_data__value__" + op : val }
        job_list = job_list.filter(**mquery)
        df_fields += [ name ]
    fields['nj'] = job_list.count()
    df_fields = list(set(df_fields))
    
    # Build dataframe for derived metrics for histograms
    metric_dict = {}
    jid_dict = { "jid" : [] }
    hist_metrics = []
    for job in job_list:
        jid_dict["jid"] += [ job.jid ]
        for name in df_fields:
            metric_set = job.metrics_data_set.all().filter(metric = name) 
            hist_metrics += [(name, metric_set[0].units)]
            for m in metric_set:
                metric_dict.setdefault(m.metric, [])
                metric_dict[m.metric] += [ m.value ]
    jid_dict.update(metric_dict)
    df = DataFrame(jid_dict)
    df = df.set_index("jid")
    hist_metrics = list(set(hist_metrics))
    
    # Build job accounting data columns of dataframe for histograms
    df_fields = ["jid", "start_time", "submit_time", "runtime", "nhosts"]
    df = df.join(DataFrame(job_list.values(*df_fields)).set_index("jid"))

    # Base fields to use in histograms added to derived metrics explicitly searched on
    hist_metrics += [("runtime", "hours"), ("nhosts", "#nodes"), ("queue_wait", "hours")]
    df["queue_wait"] = to_timedelta(df["start_time"] - df["submit_time"]).dt.total_seconds()/3600
    df["runtime"] = df["runtime"]/3600.  

    ###

    ### Pagination
    paginator = Paginator(job_list, min(100, len(job_list)))
    page_num = request.GET.get('page')

    try:
        jobs = paginator.page(page_num)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)

    fields['job_list'] = jobs
    ###

    ### Build Histogram Plots    
    plots = []
    for metric, label in hist_metrics:
        plots += [job_hist(df, metric, label)]        
    fields["script"], fields["div"] = components(gridplot(plots, ncols = 2))
    ###

    fields['logged_in'] = True
    if '?' in request.get_full_path():
        fields['current_path'] = request.get_full_path()
        
    return render(request, "machine/index.html", fields)

# Generate Histogram Plots of a List of Metrics    
def job_hist(df, metric, label):
    hover = HoverTool(tooltips = [ ("jobs", "@top"), ("bin", "[@left, @right]") ], point_policy = "snap_to_data")
    TOOLS = ["pan,wheel_zoom,box_zoom,reset,save,box_select", hover]

    values = list(df[metric].values)
    if len(values) == 0: return None

    hist, edges = histogram(values, bins = linspace(0, max(values), max(3, int(5*log(len(values))))))

    plot = figure(title = metric, toolbar_location = None, plot_height = 400, plot_width = 600, 
                  y_range = (1, max(hist)), tools = TOOLS) #  y_axis_type = "log",
    plot.xaxis.axis_label = label
    plot.yaxis.axis_label = "# jobs"

    plot.quad(top = hist, bottom = 1, left = edges[:-1], right = edges[1:])    

    return plot

def heat_map(pk):    
    data = get_data(pk)
    hm = plots.HeatMap()
    return components(hm.plot(data))

class job_dataDetailView(DetailView):
    model = job_data

    def get_queryset(self):
        queryset = super(job_dataDetailView, self).get_queryset()
        return queryset
        """
        if "is_staff" in self.request.session and self.request.session["is_staff"]:
            return queryset
        return queryset.filter(user = self.request.session["username"])
        """
    def get(self, request, *args, **kwargs):
        """
        if not check_for_tokens(self.request):
            return HttpResponseRedirect("/login_prompt")
        """
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super(job_dataDetailView, self).get_context_data(**kwargs)
        job = context['job_data']
        
        j = jid_table.jid_table(job.jid)

        context["host_list"] = j.acct_host_list

        # Build Summary Plot
        ptime = time.time()
        sp = plots.SummaryPlot(j)
        #try:
        context["mscript"], context["mdiv"] = components(sp.plot())
        #except:
        #    print("failed to generate summary plot for jid {0}".format(j.jid))
        print("plot time: {0:.1f}".format(time.time()-ptime))
        
        # Compute Lustre Usage
        try:
            llite_rw = read_sql("select event, sum(delta)/(1024*1024) as delta from job_{0} where type = 'llite' \
            and event in ('read_bytes', 'write_bytes') group by event".format(j.jid), j.conj)

            context['fsio'] = { "llite" : [ llite_rw[llite_rw["event"] == "read_bytes"]["delta"].values[0],  
                                            llite_rw[llite_rw["event"] == "write_bytes"]["delta"].values[0] ] }
        except:
            print("failed to compute Lustre data movement for jid {0}".format(j.jid))
        try:
            context["schema"] = j.schema
        except:
            print("failed to extract schema for jid {0}".format(j.jid))

        ### Specific to TACC Splunk 
        urlstring="https://scribe.tacc.utexas.edu:8000/en-US/app/search/search?q=search%20"
        hoststring=urlstring + "%20host%3D" + j.acct_host_list[0] + cfg.host_name_ext
        serverstring=urlstring + "%20mds*%20OR%20%20oss*"
        for host in j.acct_host_list[1:]:
            hoststring+="%20OR%20%20host%3D"+host+"*"

        hoststring+="&earliest="+str(j.start_time)+"&latest="+str(j.end_time)+"&display.prefs.events.count=50"
        serverstring+="&earliest="+str(j.start_time)+"&latest="+str(j.end_time)+"&display.prefs.events.count=50"
        context['client_url'] = hoststring
        context['server_url'] = serverstring
        ###
        context['logged_in'] = True

        return context

def type_detail(request, jid, type_name):
    """
    if not check_for_tokens(request):
        return HttpResponseRedirect("/login_prompt")
    """
    conj = psycopg2.connect(CONNECTION)

    # Get job accounting data
    acct_data = read_sql("""select * from job_data where jid = '{0}'""".format(jid), conj)
    # job_data accounting host names must be converted to fqdn
    acct_host_list = [h + '.' + cfg.host_name_ext for h in acct_data["host_list"].values[0]]
    
    start_time = acct_data["start_time"].dt.tz_convert('US/Central').dt.tz_localize(None).values[0]
    end_time = acct_data["end_time"].dt.tz_convert('US/Central').dt.tz_localize(None).values[0]
    
    # Get stats data and use accounting data to narrow down query
    qtime = time.time()
    sql = """drop table if exists type_detail; select * into temp type_detail from host_data where time between '{1}' and '{2}' and jid = '{0}' and type = '{3}'""".format(jid, start_time, end_time, type_name)

    # Open temporary connection
    with conj.cursor() as cur:
        cur.execute(sql)
    print("query time: {0:.1f}".format(time.time()-qtime))

    # Compare accounting host list to stats host list
    htime = time.time()
    data_host_list = set(read_sql("select distinct on(host) host from type_detail;", conj)["host"].values)
    if len(data_host_list) == 0: return context
    print("host selection time: {0:.1f}".format(time.time()-htime))
    
    # Build Type Plot
    ptime = time.time()
    sp = plots.DevPlot(conj, data_host_list)
    script,div = components(sp.plot())
    print("type plot time: {0:.1f}".format(time.time()-ptime))
    conj.close()
    return render(request, "machine/type_detail.html",
                  {"type_name" : type_name, "jobid" : jid, 
                   "tscript" : script, "tdiv" : div, "logged_in" : True})


class host_table:

    def __init__(self, host_fqdn, start_time, end_time):
        print("Initializing table for host {0}".format(host_fqdn))


        # Get stats data and use accounting data to narrow down query
        qtime = time.time()
        self.jid = host_fqdn.split('.')[0].replace('-', '_')

        sql = """drop table if exists job_{0}; select * into temp job_{0} from host_data where time between '{1}'::timestamp and '{2}'::timestamp and host = '{3}'""".format(self.jid, start_time, end_time, host_fqdn)
        print(sql)
        
        # Open temporary connection
        self.conj = psycopg2.connect(CONNECTION)
        with self.conj.cursor() as cur:
            cur.execute(sql)
        print("query time: {0:.1f}".format(time.time()-qtime))

        # Compare accounting host list to stats host list
        htime = time.time()
        self.host_list = list(set(read_sql("select distinct on(host) host from job_{0};".format(self.jid), self.conj)["host"].values))
        if len(self.host_list) == 0: return 
        print("host selection time: {0:.1f}".format(time.time()-htime))

        # Build Schema for navigation to Type Detail view
        etime = time.time()
        schema_df = read_sql("""select distinct on (type,event) type,event from job_{0} where host = '{1}'""".format(self.jid, next(iter(self.host_list))), self.conj)
        types = sorted(list(set(schema_df["type"].values)))
        self.schema = {}
        for t in types:
            self.schema[t] = list(sorted(schema_df[schema_df["type"] == t]["event"].values))
        print("schema time: {0:.1f}".format(time.time()-etime))

    def __del__(self):
        sql = """drop table if exists job_{0};""".format(self.jid)
        with self.conj.cursor() as cur:
            cur.execute(sql)
        self.conj.close() 


def host_detail(request):
    """
    if not check_for_tokens(request):
        return HttpResponseRedirect("/login_prompt")
    """

    fields = request.GET.dict()
    print(fields)
    fields = { k:v for k, v in fields.items() if v }
    print(fields)
    print("here in host_detail")
    start_time = fields['end_time__gte']
    try:
        end_time = fields['end_time__lte']
    except:
        end_time = "now()"
    
    ht = host_table(fields['host'], start_time, end_time)

    # Build Summary Plot
    ptime = time.time()
    sp = plots.SummaryPlot(ht)
    script, div = components(sp.plot())
    print("plot time: {0:.1f}".format(time.time()-ptime))

    return render(request, "machine/type_detail.html",
                  {"type_name" : fields['host'], "tag" : fields['host'], 
                   "tscript" : script, "tdiv" : div, "logged_in" : True})


def proc_detail(request, pk, proc_name):
    """
    if not check_for_tokens(request):
        return HttpResponseRedirect("/login_prompt")
    """
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
                   "host_map" : host_map, "hwm_unit" : hwm_unit, "logged_in" : True})

class ChoiceForm(forms.Form):

    queues = job_data.objects.distinct("queue").values_list("queue", flat = True)
    states = job_data.objects.exclude(state__contains = "CANCELLED by").distinct("state").values_list("state", flat = True)

    QUEUECHOICES = [('','')] + [(q, q) for q in queues]
    print(QUEUECHOICES)
    queue = forms.ChoiceField(choices=QUEUECHOICES, widget=forms.Select(choices=QUEUECHOICES))
    
    STATECHOICES = [('','')] + [(s, s) for s in states]
    print(STATECHOICES)
    state = forms.ChoiceField(choices=STATECHOICES, widget=forms.Select(choices=STATECHOICES))

