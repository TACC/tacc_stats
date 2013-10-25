from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from stats.models import Job
from stats.views import *

urlpatterns = patterns('',
                       url(r'^$',dates, name='dates'),

                       url(r'^date/(?P<date>\d{4}-\d{2}-\d{2})/$', index),

                       url(r'^date/(?P<date>\d{4}-\d{2}-\d{2})/job/(?P<pk>\d+)/$',
                           JobDetailView.as_view()),

                       url(r'^date/\d{4}-\d{2}-\d{2}/job/(?P<pk>\d+)/(?P<type_name>\w+)/$',
                           type_detail, name = 'type_detail'),

                       url(r'^type_plot/(?P<pk>\d+)/(?P<type_name>\w+)/$', 
                           type_plot, name = 'type_plot'),

                       url(r'^master_plot/(?P<pk>\d+)/$', 
                           master_plot, name = 'master_plot'),

                       url(r'^jobs_summary/(?P<date>\d{4}-\d{2}-\d{2})/$', 
                           jobs_summary, name = 'jobs_summary' ),

                       url(r'^search/$',search, name='search'),
)
