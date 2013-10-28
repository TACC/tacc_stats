from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from stats.models import Job
from stats.views import *

urlpatterns = patterns('',
                       url(r'^$',dates, name='dates'),

                       url(r'^job/(?P<pk>\d+)/$',
                           JobDetailView.as_view(), name='job'),

                       url(r'^job/(?P<pk>\d+)/(?P<type_name>\w+)/$',
                           type_detail, name = 'type_detail'),

                       url(r'^type_plot/(?P<pk>\d+)/(?P<type_name>\w+)/$', 
                           type_plot, name = 'type_plot'),

                       url(r'^master_plot/(?P<pk>\d+)/$', 
                           master_plot, name = 'master_plot'),

                       url(r'^heat_map/(?P<pk>\d+)/$', 
                           heat_map, name = 'heat_map'),

                       url(r'^date_summary/(?P<date>\d{4}-\d{2}-\d{2})/$',
                           hist_summary, name = 'date_summary', 
                           ),
                       url(r'^uid_summary/(?P<uid>\d+)/$', 
                           hist_summary, name = 'uid_summary' ),
                       url(r'^project_summary/(?P<project>\w+.*\w+)/$', 
                           hist_summary, name = 'project_summary' ),

                       url(r'^date/(?P<date>\d{4}-\d{2}-\d{2})/$', 
                           index, name='date_view'),
                       url(r'^uid/(?P<uid>\d+)/$',
                           index, name='uid_view'),
                       url(r'^project/(?P<project>\w+.*\w+)/$',
                           index, name='project_view'),

                       url(r'^search/$',search, name='search'),
)
