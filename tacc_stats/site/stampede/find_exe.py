#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "tacc_stats.site.tacc_stats_site.settings")
import django
django.setup()

from tacc_stats.site.stampede.models import Job
    
def search(kwargs):
    print "{0:10}  {1:20}  {2:10}  {3}".format('id', 'exe', 'user', 'sus')
    for f in kwargs:
        job = Job.objects.get(id=f)
        print "{0:10}  {1:20}  {2:10}  {3:0.2f}".format(job.id,job.exe,job.user,job.nodes*16*job.run_time/3600.)

file_list = sys.argv[1:]
search(file_list)
