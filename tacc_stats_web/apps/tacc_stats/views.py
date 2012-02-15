import sys
sys.path.append('/home/dmalone/other/src/tacc_stats/monitor')

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render
from django.views.generic import DetailView, ListView

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

from tacc_stats.models import Job
import job

SHELVE_DIR = '/home/tacc_stats/sample-jobs/jobs'

SHELVE_DIR = '/home/dmalone/sample-jobs/jobs'

from forms import SearchForm

SHELVE_DIR = '/home/dmalone/sample-jobs/jobs'

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

    intensity = NP.diff(files_opened)

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

    intensity = NP.log(NP.diff(flops_used)) / math.log(RANGER_MAX_FLOPS)
    
    return intensity

def _flops_intensity(job, host):
    """
    Helper function which creates a time-array of flops used by a job on a host
    
    The value is a percent of the maximum value of the array
    
    Arguments:
    job -- the job being accessed
    host -- the host being charted
    """
    flops_used = [0] * job.times.size

    cpu_data = job.hosts[host].interpret_amd64_pmc_cpu()

    for key, val in cpu_data.iteritems():
        if (key[:4] == 'core'):
            flops_used = flops_used + val['SSEFLOPS']

    difference = NP.diff(flops_used)
    intensity = NP.append(0, difference) / difference.max()
    return intensity

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

    PLT.subplot(num_hosts, 1, n)
    PLT.pcolor(x, NP.array([0, 1]), intensity, cmap=matplotlib.cm.Reds, vmin = 0, vmax = 1, edgecolors='none')

    if (n != num_hosts):
        PLT.xticks([])
    else:
        PLT.xlabel('Hours From Job Beginning')
    PLT.yticks([])

    PLT.autoscale(enable=True,axis='both',tight=True)

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

    f = PLT.gcf()

    f.set_size_inches(10,num_hosts*.3+1.5)
    return figure_to_response(f)

@csrf_protect
def search(request):
    """ 
    Creates a search form that can be used to navigate through the list 
    of jobs.
    """
    if request.method == 'POST':
        print request.POST

        form = SearchForm(request.POST)
        query = request.POST

        job_list = Job.objects.all()

        if form["acct_id"].value():
            job_list = job_list.filter(acct_id = form["acct_id"].value())
        if form["owner"].value():
            job_list = job_list.filter(owner = form["owner"].value())
        if form["begin"].value():
            job_list = job_list.filter(begin__gte = form["begin"].value())
        if form["end"].value():
            job_list = job_list.filter(end__lte = form["end"].value())

    else:
        form = SearchForm()
        job_list = Job.objects.order_by('-begin')[:200]

    return render(request, 'tacc_stats/search.html', {'form' : form, 'job_list' : job_list })

class JobListView(ListView):

    def get_queryset(self):
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
