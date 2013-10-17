from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.generic import DetailView, ListView
import matplotlib, string
import matplotlib.pyplot as plt
from pylab import figure, hist, plot

from stats.models import Job

import os,sys
sys.path.append('/Users/rtevans/tacc_stats/monitor')
sys.path.append('/Users/rtevans/tacc_stats/analyze/process_pickles')
import masterplot as mp
import job_stats as data
import  cPickle as pickle 

path = '/Users/rtevans/pickles/'

def index(request):
    
    Job.objects.all().delete()

    for jobid in os.listdir(path):
        try:
            with open(path+jobid) as f:
                data = pickle.load(f)
            if len(data.times) == 0: continue
            del data.acct['yesno'], data.acct['unknown']
        except: continue

        fields = data.acct
        fields['path'] = path+jobid

        job_model, created = Job.objects.get_or_create(**fields) 

    job_list = Job.objects.all().order_by('-id')

    return render_to_response("stats/index.html", {'job_list' : job_list})

def figure_to_response(f):
    response = HttpResponse(content_type='image/png')
    f.savefig(response, format='png')
    plt.close(f)
    f.clear()
    return response

def jobs_summary(request):
    # Run times
    job_times = [job.timespent / 3600. for job in Job.objects.all()]
    fig = figure()
    ax = fig.add_subplot(211)
    ax.hist(job_times, len(job_times))
    ax.set_title('Run Times (hrs)')
    ax.set_ylabel('# of jobs')

    # Number of cores
    job_size = [job.cores for job in Job.objects.all()]
    ax = fig.add_subplot(212)
    ax.hist(job_size, len(job_size))
    ax.set_title('Cores')
    ax.set_ylabel('# of jobs')
   
    return figure_to_response(fig)

def master_plot(request, pk):
    job = Job.objects.get(id = pk)
    fig = mp.master_plot(job.path)
    return figure_to_response(fig)

class JobDetailView(DetailView):

    model = Job

    def get_context_data(self, **kwargs):
        context = super(JobDetailView, self).get_context_data(**kwargs)
        job = context['job']

        with open(job.path) as f:
            data = pickle.load(f)
        job.stats = data
        job.save()

        type_list = []
        for host_name, host in job.stats.hosts.iteritems():
            for type_name, type in host.stats.iteritems():
                schema = job.stats.get_schema(type_name).desc
                schema = string.replace(schema,',E',' ')
                schema = string.replace(schema,',',' ')
                type_list.append( (type_name, schema) )
            break
        dev_list = sorted(type_list, key = lambda type: type[0])
        context['type_list'] = type_list
        return context

def type_plot(request, pk, type_name):


    job = Job.objects.get(id = pk)
    data = job.stats

    schema = data.get_schema(type_name).desc
    schema = string.replace(schema,',E',' ')
    schema = string.replace(schema,' ,',',').split()

    raw_stats = data.aggregate_stats(type_name)[0]  
    nr_events = len(schema)

    import matplotlib.ticker as tic
    from numpy import divide, diff
    nt = len(data.times)

    tmid = (data.times[1:]+data.times[0:nt-1])/2.0
    tmid -= data.times[0]
    tmid /= 3600.
    fig, axarr = plt.subplots(nr_events, sharex=True, figsize=(10,nr_events*4))

    for i in range(nr_events):
        rate = divide(diff(raw_stats[:,i]),diff(data.times))
        axarr[i].plot(tmid, rate)
        axarr[i].set_ylabel(schema[i])
        
    axarr[0].set_title("Count Rates (1/s)")
    axarr[-1].set_xlabel("Time (hr)")
    fig.subplots_adjust(hspace=0.0)
    fig.tight_layout()
    response = HttpResponse(content_type='image/png')
    fig.savefig(response, format='png')
    plt.close(fig)
    fig.clear()
    return response


def type_detail(request, pk, type_name):

    job = Job.objects.get(id = pk)
    data = job.stats

    schema = data.get_schema(type_name).desc
    schema = string.replace(schema,',E',' ')
    schema = string.replace(schema,' ,',',').split()

    raw_stats = data.aggregate_stats(type_name)[0]  

    stats = []
    for t in range(len(raw_stats)):
        temp = []
        for event in range(len(raw_stats[t])):
            temp.append(raw_stats[t,event])
        stats.append((data.times[t],temp))


    return render_to_response("stats/type_detail.html",{"type_name" : type_name, "jobid" : pk, "stats_data" : stats, "schema" : schema})
    
