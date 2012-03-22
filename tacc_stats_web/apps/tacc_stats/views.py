import sys
sys.path.append('/home/dmalone/other/src/backup/monitor')

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render
from django.views.generic import DetailView, ListView
from django.db.models import Q
from django.utils.simplejson import dumps, loads, JSONEncoder

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg
from pylab import figure, axes, pie, title, hist, xlabel, ylabel
from matplotlib import pyplot as PLT
from matplotlib.colors import LogNorm

import shelve
import job
import numpy as NP
import math

import time

import demjson
json = demjson.JSON(compactly=False)
jsonify = json.encode

from dojoserializer import serialize

from tacc_stats.models import Job, COLORS, Node
import job

SHELVE_DIR = '/home/tacc_stats/sample-jobs/jobs'

from forms import SearchForm

def index(request):
    """ Creates a list of all currently running jobs """
    job_list = Job.objects.all().order_by('-acct_id')[:5]
    return render_to_response("tacc_stats/index.html", {'job_list':job_list})

def figure_to_response(f):
    """ Creates a png image to be displayed in an html file """
    canvas = FigureCanvasAgg(f)
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    matplotlib.pyplot.close(f)
    return response

def job_timespent_hist(request):
    """ Makes a histogram displaying all the jobs by their time spent running """
    f = figure()
    runtimes = [job.end - job.begin for job in Job.objects.all()]
    job_times = [runtime / 60.0 for runtime in runtimes]
    hist(job_times, 50, log=True)
    title('Times spent by jobs')
    xlabel('Time (m)')
    ylabel('Number of jobs')
    return figure_to_response(f)

def job_memused_hist(request):
    """ Makes a histogram displaying all the jobs by their memory used """
    f = figure()
    job_mem = [job.mem_MemUsed / 2**30 for job in Job.objects.all()]
    hist(job_mem, 40, log=True)
    title('Memory used by jobs')
    xlabel('Memory (GB)')
    ylabel('Number of jobs')
    return figure_to_response(f)

def _memory_intensity(job, host):
    """
    Helper function which creates an time-array of the percent memory utilized by a specific job on a specific host.

    Arguments:
    job -- the job being accessed
    host -- the host being charted
    """
    memused = memtotal = [0] * job.times.size

    memused_index = job.schema['mem'].keys['MemUsed'].index
    memtotal_index = job.schema['mem'].keys['MemTotal'].index

    for slot in job.hosts[host].stats['mem']:
        memused = memused + job.hosts[host].stats['mem'][slot][: , memused_index]
        memtotal = memtotal + job.hosts[host].stats['mem'][slot][: , memtotal_index]

    intensity = memused / memtotal
    return intensity

def _files_open_intensity(job, host):
    """
    Helper function which creates an time-array of the files opened by a specific job on a specific host.

    The value is a percent of the maximum value in the array. The initial datapoint is set to zero to preserve the length of the list

    Arguments:
    job -- the job being accessed
    host -- the host being charted
    """
    files_opened = [0] * job.times.size

    files_opened_index = job.schema['llite'].keys['open'].index

    for filesystem in job.hosts[host].stats['llite']:
        files_opened = files_opened + job.hosts[host].stats['llite'][filesystem][: , files_opened_index]

    intensity = NP.diff(files_opened) / NP.diff(job.times)

    return intensity

def _flops_intensity(job, host):
    """
    Helper function which creates a time-array of flops used by a job on a host

    The value is a percent of the maximum value of the array

    Arguments:
    job -- the job being accessed
    host -- the host being charted
    """
    RANGER_MAX_FLOPS = 88326000000000
    flops_used = [0] * job.times.size

    cpu_data = job.hosts[host].interpret_amd64_pmc_cpu()

    for key, val in cpu_data.iteritems():
        if (key[:4] == 'core'):
            flops_used = flops_used + val['SSEFLOPS']

    intensity = NP.diff(flops_used) / NP.diff(job.times) / 10 ** 9

    return intensity

#def _default_intensity(job, host, schema, entry)
#    """ The intensity function defaulted to for a given statistic """
    

def create_subheatmap(intensity, job, host, n, num_hosts):
    """
    Creates a heatmap in a subplot.

    Arguments:
    intensity -- the values of the intensity being plotted. Must be same length as job.times
    job -- the current job being plotted
    host -- the host  being charted
    n -- the subplot number of the specific host
    num_hosts -- the total number of hosts to be plotted
    """
    length = job.times.size
    end = job.end_time
    start = job.start_time

    x = NP.linspace(0, (end - start) / 3600.0, length * 1)

    intensity = NP.array([intensity]*2, dtype=NP.float64)

    PLT.subplot(num_hosts+1, 1, n)
    PLT.pcolor(x, NP.array([0, 1]), intensity, cmap=matplotlib.cm.Reds, vmin = 0, vmax = math.ceil(NP.max(intensity)), edgecolors='none')

    if (n != num_hosts):
        PLT.xticks([])
    else:
        PLT.xlabel('Hours From Job Beginning')
    PLT.yticks([])

    #PLT.autoscale(enable=True,axis='both',tight=True)

    host_name = host.replace('.tacc.utexas.edu', '')
    PLT.ylabel(host_name, fontsize ='small', rotation='horizontal')

def create_heatmap(request, job_id, trait):
    """
    Creates a heatmap with its intensity correlated with a specific datapoint
    Arguments:
    job_id -- the SGE identification number of the job being charted
    trait -- the type of heatmap being created, can take values:
             memory -- intensity is correlated to memory used by the job
             files -- intensity is correlated to the number of files opened
             flops -- intenisty is correlated to the number of floating point
                      operations performed by the host
    """
    job_shelf = shelve.open(SHELVE_DIR)

    job = job_shelf[job_id]

    hosts = job.hosts.keys()
            
    n = 1 
    num_hosts = len(job.hosts)
    PLT.subplots_adjust(hspace = 0)

    if (trait == 'memory'):
        PLT.suptitle('Memory Used By Host', fontsize = 12)
    elif (trait == 'files'):
        PLT.suptitle('Files Opened By Host', fontsize = 12)
    elif (trait == 'flops'):
        PLT.suptitle('Flops Performed By Host', fontsize = 12)

    max = 1

    for host in hosts:
        intensity = [0]

        if (trait == 'memory'):
            intensity = _memory_intensity(job, host)
        elif (trait == 'files'):
            intensity = _files_open_intensity(job, host)
        elif (trait == 'flops'):
            intensity = _flops_intensity(job, host)

        create_subheatmap(intensity, job, host, n, num_hosts)
        n += 1


    max = math.ceil(NP.max(intensity))
    f = PLT.gcf()
#    cb = PLT.colorbar(orientation='vertical', fraction=5.0, pad = 1.0)
    cax = f.add_axes([0.91, 0.10, 0.03, 0.8])
    cb = PLT.colorbar(orientation='vertical', cax=cax, ticks=[0, max])
    
    if (trait == 'memory'):
        cb.set_label('% Memory')
    elif (trait == 'files'):
        cb.set_label('Files Opened Per Second')
    elif (trait == 'flops'):
        cb.set_label('GFlops (Peak ~150)')

#    PLT.setp(cb, 'Position', [.8314, .11, .0581, .8150])

    f.set_size_inches(10,num_hosts*.3+1.5)
    return figure_to_response(f)

@csrf_protect
def search(request):
    """ 
    Creates a search form that can be used to navigate through the list 
    of jobs.
    """
    PAGE_LENGTH = 20
    query_string = ""

    if request.method == 'POST':
        print request.POST

        form = SearchForm(request.POST)
        query = request.POST.copy()

        if query.get('csrfmiddlewaretoken'):
            query.__delitem__('csrfmiddlewaretoken')
        
        query_string = "&"
	query_string += query.urlencode()

        job_list = Job.objects.all()

    else:
        form = SearchForm(request.GET)
        query = request.GET.copy()

        if query.get('p'):
            query.__delitem__('p')
        if query.get('csrfmiddlewaretoken'):
            query.__delitem__('csrfmiddlewaretoken')

        query_string = '&'
        query_string += query.urlencode()

        job_list = Job.objects.all()

    if form["acct_id"].value():
        job_list = job_list.filter(acct_id = form["acct_id"].value())
    if form["owner"].value():
        job_list = job_list.filter(owner = form["owner"].value())
    if form["begin"].value():
        job_list = job_list.filter(begin__gte = form["begin"].value())
    if form["end"].value():
        job_list = job_list.filter(end__lte = form["end"].value())
#   if form["hosts"].value():
#       job_list = job_list.filter(hosts__in=form["hosts"].value())
        
    num_jobs = job_list.count()

    start = 0
    page = 0
    end = PAGE_LENGTH

    if request.GET.get('p'):
        page = int(request.GET.get('p'))
        start = int(request.GET.get('p')) * PAGE_LENGTH
        end = start + PAGE_LENGTH

    job_list = job_list[start : end]

    num_pages = int(math.ceil(num_jobs / PAGE_LENGTH))

    pages = create_pagelist(num_pages, PAGE_LENGTH, page)

    return render(request, 'tacc_stats/search.html', {'form' : form, 'job_list' : job_list, 'COLORS' : COLORS, 'pages' : pages, 'page' : page, 'query_string' : query_string})

def list_hosts(request):
    """ Creates a list of hosts with their corresponding jobs """
    PAGE_LENGTH = 10

    num_hosts = Node.objects.all().count()
    num_pages = int(math.ceil(num_hosts / PAGE_LENGTH))

    start = 0
    page = 0
    end = PAGE_LENGTH

    if request.GET.get('p'):
        page = int(request.GET.get('p'))
        start = int(request.GET.get('p')) * PAGE_LENGTH
        end = start + PAGE_LENGTH

    hosts = Node.objects.all().order_by('name')[start:end]

    pages = create_pagelist(num_pages, PAGE_LENGTH, page)

    jobs_by_host = {}
    for host in hosts:
        host_jobs = Job.objects.filter(hosts = host).order_by('begin')
        jobs_by_host[host.name] = host_jobs

    return render_to_response('tacc_stats/hosts.html', {'hosts' : hosts, 'jobs_by_host' : jobs_by_host, 'pages' : pages, 'page' : page })

def create_pagelist(num_pages, PAGE_LENGTH, page):
    """ Creates a formatted list of pages which can be hyperlinked """
    pages = []

    if num_pages >= 0 and num_pages <= 6:
        pages = range(num_pages)
    else:
        if page <= 2:
            pages = range(3 + page)
            pages.append('...')
            pages += range(num_pages - 3, num_pages)
        elif page >= (num_pages - 3):
            pages = range(3)
            pages.append('...')
            pages += range(page - 2, num_pages)
        else:
            if num_pages <= 9:
                pages = range(num_pages)
            else:
                pages = range(3)
                pages.append('...')
                pages += range(page - 1, page + 2)
                pages.append('...')
                pages += range(num_pages - 3, num_pages)

    return pages

def render_json(request):
    """ Creates a json page for a dojo data grid to query the jobs data from """
    jobs = Job.objects.all().values()
    print jobs
    num_jobs = Job.objects.count()
#    json_data = serialize(jobs)
    json_data = jsonify({"numRows" : num_jobs, 'items': jobs})
    return HttpResponse(json_data, mimetype="application/json")

def get_job(request, host, id):
    """ Creates a detailed view of a specific job """
    job = Job.objects.get(acct_id = id)
    return render_to_response('tacc_stats/job_detail.html', {'job' : job})

def data(request):
    """ Creates a page with data as defined by GET """
    search = request.GET
    start = int(search.get('start'))
    end = start + int(search.get('count'))

    job_list = Job.objects.order_by('-begin')[start:end]
  
    num_jobs = Job.objects.count()

    json_data = serialize(job_list)
    
    json_data = json_data.replace(u"\"numRows\": 20", u"\"numRows\": %i" % (num_jobs) )

    return HttpResponse(json_data, mimetype="application/json")

class JobListView(ListView):
    """
    Class which extends the ListView class and replaces specific searchs
    """
    def get_queryset(self):
        """
        Creates a default query of the first 200 jobs
        """
        if self.request.method == 'POST':
            query = self.request.POST
            return Job.objects.order_by('-begin')[:200]
            #return Job.objects.filter(
            #        owner = query.__getitem__("owner"),
            #        begin = query.__getitem__("begin"),
            #        end = query.__getitem__("end"),
            #        hosts = query.__getitem__("hosts"),
            #        acct_id = query.__getitem__("acct_id")
            #        )
        else:
            return Job.objects.order_by('-begin')[:200]
