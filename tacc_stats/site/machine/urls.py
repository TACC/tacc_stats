from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from tacc_stats.site.machine.models import Job
from tacc_stats.site.machine.views import *

urlpatterns = patterns('',
                       url(r'^$',dates, name='dates'),

                       url(r'^job/(?P<pk>\d+)/$',
                           JobDetailView.as_view(), name='job'),
                       url(r'^job/(?P<pk>\d+)/(?P<type_name>\w+)/$',
                           type_detail, name = 'type_detail'),

                       url(r'^type_plot/(?P<pk>\d+)/(?P<type_name>\w+)/$', 
                           type_plot, name = 'type_plot'),
                       url(r'^sys_plot/(?P<pk>\d+)/$', 
                           sys_plot, name = 'sys_plot'),
                       url(r'^master_plot/(?P<pk>\d+)/$', 
                           master_plot, name = 'master_plot'),
                       url(r'^heat_map/(?P<pk>\d+)/$', 
                           heat_map, name = 'heat_map'),

                       url(r'^date_summary/(?P<date>\d{4}-\d{2}-\d{2})/$',
                           hist_summary, name = 'date_summary', 
                           ),
                       url(r'^uid_summary/(?P<uid>\d+)/$', 
                           hist_summary, name = 'uid_summary' ),
                       url(r'^user_summary/(?P<user>.*)/$', 
                           hist_summary, name = 'user_summary' ),
                       url(r'^project_summary/(?P<project>.*)/$', 
                           hist_summary, name = 'project_summary' ),
                       url(r'^exe_summary/(?P<exe__icontains>.*)/$', 
                           hist_summary, name = 'exe_summary' ),

                       url(r'^date/(?P<date>\d{4}-\d{2}-\d{2})/$', 
                           index, name='date_view'),
                       url(r'^date/(?P<date>\d{4}-\d{2})/$', 
                           index, name='date_view'),

                       url(r'^uid/(?P<uid>\d+?)/$',
                           index, name='uid_view'),
                       url(r'^user/(?P<user>\w+?)/$',
                           index, name='user_view'),
                       url(r'^project/(?P<project>.+?)/$',
                           index, name='project_view'),
                       url(r'^exe/(?P<exe__icontains>.+?)/$',
                           index, name='exe_view'),
                       
                       url(r'^search/$',search, name='search'),
                       )
