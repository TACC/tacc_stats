from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from stats.models import Job
from stats.views import *

urlpatterns = patterns('',
    url(r'^$', index),
    url(r'^joblist$',
        ListView.as_view(
            queryset=Job.objects.order_by('-id')[:200])),
    url(r'^job/(?P<pk>\d+)/$',
        JobDetailView.as_view()),

    url(r'^job/(?P<pk>\d+)/(?P<type_name>\w+)/$',type_detail, name = 'type_detail'),

    url(r'^type_plot/(?P<pk>\d+)/(?P<type_name>\w+)/$', type_plot, name = 'type_plot'),
    url(r'^master_plot/(?P<pk>\d+)/$', master_plot, name = 'master_plot'),
    url(r'^jobs_summary$', jobs_summary ),
)
