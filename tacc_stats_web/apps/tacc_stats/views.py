from django.http import HttpResponse
from django.shortcuts import render_to_response

from pylab import figure, axes, pie, title, hist, xlabel, ylabel
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg

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
