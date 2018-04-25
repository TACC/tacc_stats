from django.conf.urls import url
from django.views.generic import DetailView, ListView
from tacc_stats.site.machine.models import Job
from tacc_stats.site.machine.views import *

urlpatterns = [
                       url(r'^$',dates, name='dates'),

                       url(r'^job/(?P<pk>\d+)/$',
                           JobDetailView.as_view(), name='job'),
                       url(r'^job/(?P<pk>\d+)/(?P<type_name>\w+)/$',
                           type_detail, name = 'type_detail'),

                       url(r'^proc/(?P<pk>\d+)/(?P<proc_name>.*)/$',
                           proc_detail, name = 'proc_detail'),

                       url(r'^date/(?P<date>\d{4}-\d{2}-\d{2})/$', 
                           index, name='date_view'),
                       url(r'^date/(?P<date>\d{4}-\d{2})/$', 
                           index, name='date_view'),

                       url(r'^uid/(?P<uid>\d+?)/$',
                           index, name='uid_view'),
                       url(r'^user/(?P<user>.+?)/$',
                           index, name='user_view'),
                       url(r'^project/(?P<project>.+?)/$',
                           index, name='project_view'),
                       url(r'^exe/(?P<exe__icontains>.+?)/$',
                           index, name='exe_view'),
                       
                       url(r'^search/$',search, name='search'),
]

