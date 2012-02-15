from django.conf.urls.defaults import patterns, url
from django.views.generic import DetailView, ListView
from tacc_stats.models import Job
from tacc_stats.views import index, job_memused_hist, job_timespent_hist, create_heatmap, search, JobListView

urlpatterns = patterns('',
    url(r'^$', index),
    url(r'^joblist$',
        JobListView.as_view()),
    url(r'^job/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Job,
        #    template_name='tacc_stats/detail.html',
        )),
    url(r'^job_memused_hist$', job_memused_hist ),
    url(r'^job_timespent_hist$', job_timespent_hist ),
    url(r'^job_mem_heatmap/(\d+)/$', create_heatmap, {'trait' : 'memory'}),
    url(r'^job_files_opened_heatmap/(\d+)/$', create_heatmap, {'trait' : 'files'}),
    url(r'^job_flops_heatmap/(\d+)/$', create_heatmap, {'trait' : 'flops'}),
    url(r'^search/$', search ),
)
