#!/usr/bin/env python
import os
os.environ['DJANGO_SETTINGS_MODULE']='tacc_stats.site.tacc_stats_site.settings'

from tacc_stats.site.stampede.models import Host, Job
    
from matplotlib import cm,colors
from matplotlib.figure import Figure    
import numpy as np
from matplotlib.backends.backend_pdf import FigureCanvasPdf
from django.db.models import Q
from datetime import datetime
racks = []
nodes = []

hosts = {}
jobs = {}

cpi = {}
metric = 'cpi'

for host in Host.objects.values_list('name',flat=True).distinct():
    r,n=host.split('-')
    if 'c400' in r: continue
    racks.append(r)
    nodes.append(n)
racks = sorted(set(racks))
nodes = sorted(set(nodes))

for job in Job.objects.filter(date=datetime.strptime('2014-08-04','%Y-%m-%d')).filter(nodes__gt = 0).exclude(Q(**{metric : None}) | Q(**{metric : float('nan')})).all(): 
    for host in job.host_set.all():
        try:
            cpi[host.name] += job.cpi*job.run_time
            jobs[host.name] += job.run_time
        except:
            cpi[host.name] = job.cpi*job.run_time
            jobs[host.name] = job.run_time

x = np.zeros((len(nodes),len(racks)))
for r in range(len(racks)):
    for n in range(len(nodes)):
        name = str(racks[r])+'-'+str(nodes[n])
        try:
            x[n][r] = cpi[name]/jobs[name]
        except: pass
fig = Figure(figsize=(20,10))
ax=fig.add_subplot(1,1,1)

ax.set_yticks(range(len(nodes)))
ax.set_yticklabels(nodes,fontsize=4)
ax.set_xticks(range(len(racks)))
ax.set_xticklabels(racks,fontsize=4,rotation=90)


pcm = ax.pcolor(np.array(range(len(racks)+1)),np.array(range(len(nodes)+1)),x)
fig.colorbar(pcm)

canvas = FigureCanvasPdf(fig)
fig.savefig('host_view')


"""
from datetime import datetime

for job in Job.objects.filter(date=datetime.strptime('2014-01-01',"%Y-%m-%d")):
    print job
    for host in job.host_set.all():
        print host
"""
