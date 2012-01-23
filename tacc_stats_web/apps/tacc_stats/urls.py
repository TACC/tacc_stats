from django.conf.urls.defaults import patterns, url
from django.views.generic import DetailView, ListView
from tacc_stats.models import Job
from tacc_stats.views import index, job_memused_hist, job_timespent_hist, job_mem_heatmap

urlpatterns = patterns('',
    url(r'^$', index),
    url(r'^joblist$',
        ListView.as_view(
            queryset=Job.objects.order_by('-acct_id')[:200],
        #    context_object_name='latest_job_list',
        #    template_name='tacc_stats/index.html',
        )),
    url(r'^job/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Job,
        #    template_name='tacc_stats/detail.html',
        )),
    url(r'^job_memused_hist$', job_mem_heatmap ),
    url(r'^job_timespent_hist$', job_timespent_hist ),
    url(r'^job_mem_heatmap$', job_mem_heatmap),
)
