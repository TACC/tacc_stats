import sys
sys.path.append('/home/dmalone/')

from django.http import HttpResponse
from django.shortcuts import render_to_response

from pylab import figure, axes, pie, title, hist, xlabel, ylabel
import matplotlib
from matplotlib import pyplot as PLT
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pickle
import job
import numpy as NP

from tacc_stats.models import Job

def index(request):
    job_list = Job.objects.all().order_by('-acct_id')[:5]
    return render_to_response("tacc_stats/index.html", {'job_list':job_list})

def figure_to_response(f):
    canvas = FigureCanvasAgg(f)
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    matplotlib.pyplot.close(f)
    return response

def job_timespent_hist(request):
    f = figure()
    job_times = [job.timespent / 60 for job in Job.objects.all()]
    hist(job_times, 50, log=True)
    title('Times spent by jobs')
    xlabel('Time (m)')
    ylabel('Number of jobs')
    return figure_to_response(f)

def job_memused_hist(request):
    f = figure()
    job_mem = [job.MemUsed / 2**30 for job in Job.objects.all()]
    hist(job_mem, 40, log=True)
    title('Memory used by jobs')
    xlabel('Memory (GB)')
    ylabel('Number of jobs')
    return figure_to_response(f)

def memory_intensity(job, host):
    memused = memtotal = [0] * job.times.size

    for slot in job.hosts[host].stats['mem']:
        memused = memused + job.hosts[host].stats['mem'][slot][: , 1]
        memtotal = memtotal + job.hosts[host].stats['mem'][slot][: , 0]

    intensity = memused / memtotal
    return intensity

def files_open_intensity(job, host):
    files_opened = [0] * job.times.size

    for filesystem in job.hosts[host].stats['llite']:
        files_opened = files_opened + job.hosts[host].stats['llite'][filesystem][: , 7]

    difference = NP.diff(files_opened)
    intensity = NP.append(0, difference) / difference.max()
    return intensity

def create_subheatmap(intensity, job, host, n, num_hosts):
    length = job.times.size
    end = job.end_time
    start = job.start_time

    x = NP.linspace(0, (end - start) / 3600, length * 10)

    intensity = NP.interp(x, NP.linspace(0, (end - start) / 3600, length), intensity)

    intensity = NP.array([intensity]*2, dtype=NP.float64)

    plot = num_hosts * 100 + 10 + n
    PLT.subplot(plot)
    PLT.pcolor(x, NP.array([0, 1]), intensity, cmap=matplotlib.cm.Reds, vmin = 0, vmax = 1)

    if (n != num_hosts):
        PLT.xticks([])
    else:
        PLT.xlabel('Hours From Job Beginning')
    PLT.yticks([])

    host_name = host.replace('.tacc.utexas.edu', '')
    PLT.ylabel(host_name, fontsize ='small', rotation='horizontal')

def job_mem_heatmap(request):
    fp = open('/home/dmalone/2255593.pic','rb')
    job = pickle.load(fp)

    hosts = job.hosts.keys()
    
    n = 1
    num_hosts = len(job.hosts)
    PLT.subplots_adjust(hspace = 0)
    PLT.suptitle('Memory Used By Host', fontsize = 12)

    for host in hosts:
	intensity = memory_intensity(job, host)
        create_subheatmap(intensity, job, host, n, num_hosts)
        n += 1
	
    f = PLT.gcf()

    f.set_size_inches(10,num_hosts*.3+1.5)
    return figure_to_response(f)

def job_files_open_heatmap(request):
    fp = open('/home/dmalone/2255593.pic','rb')
    job = pickle.load(fp)

    hosts = job.hosts.keys()
   
    n = 1
    num_hosts = len(job.hosts)
    PLT.subplots_adjust(hspace = 0)
    PLT.suptitle('Files Used By Host', fontsize = 12)

    for host in hosts:
        intensity = files_open_intensity(job, host)
        create_subheatmap(intensity, job, host, n, num_hosts)
        n += 1

    f = PLT.gcf()

    f.set_size_inches(10,num_hosts*.3+1.5)
    return figure_to_response(f)

