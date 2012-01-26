import sys
sys.path.append('/home/dmalone/')

from django.http import HttpResponse
from django.shortcuts import render_to_response

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg
from pylab import figure, axes, pie, title, hist, xlabel, ylabel
from matplotlib import pyplot as PLT
import shelve
import job
import numpy as NP

from tacc_stats.models import Job

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

    difference = NP.diff(files_opened)
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

    x = NP.linspace(0, (end - start) / 3600., length * 1)

    intensity = NP.array([intensity]*2, dtype=NP.float64)

    PLT.subplot(num_hosts, 1, n)
    PLT.pcolor(x, NP.array([0, 1]), intensity, cmap=matplotlib.cm.Reds, vmin = 0, vmax = 1)

    if (n != num_hosts):
        PLT.xticks([])
    else:
        PLT.xlabel('Hours From Job Beginning')
    PLT.yticks([])

    PLT.autoscale(enable=True,axis='both',tight=True)

    host_name = host.replace('.tacc.utexas.edu', '')
    PLT.ylabel(host_name, fontsize ='small', rotation='horizontal')

def job_mem_heatmap(request, job_id):
    """
    Creates a heatmap with intensity correlated with the amount of memory used by the job
    """
    job_shelf = shelve.open(SHELVE_DIR)

    job = job_shelf[job_id]

    hosts = job.hosts.keys()

    n = 1
    num_hosts = len(job.hosts)
    PLT.subplots_adjust(hspace = 0)
    PLT.suptitle('Memory Used By Host', fontsize = 12)

    for host in hosts:
        intensity = _memory_intensity(job, host)
        create_subheatmap(intensity, job, host, n, num_hosts)
        n += 1

    f = PLT.gcf()

    f.set_size_inches(10,num_hosts*.3+1.5)
    return figure_to_response(f)
    
def job_files_open_heatmap(request, job_id):
    """
    Creates a heatmap with intensity correlated with the amount of files a job opens
    """
    job_shelf = shelve.open(SHELVE_DIR)

    job = job_shelf[job_id]

    hosts = job.hosts.keys()

    n = 1
    num_hosts = len(job.hosts)
    PLT.subplots_adjust(hspace = 0)
    PLT.suptitle('Files Used By Host', fontsize = 12)

    for host in hosts:
        intensity = _files_open_intensity(job, host)
        create_subheatmap(intensity, job, host, n, num_hosts)
        n += 1

    f = PLT.gcf()

    f.set_size_inches(10,num_hosts*.3+1.5)
    return figure_to_response(f)
