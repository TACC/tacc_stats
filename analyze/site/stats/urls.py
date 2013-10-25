from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView
from stats.models import Job
from stats.views import *

urlpatterns = patterns('',
                       url(r'^$',dates, name='dates'),

                       url(r'^date/(?P<date>\d{4}-\d{2}-\d{2})/$', index),

                       url(r'^job/(?P<pk>\d+)/$',
                           JobDetailView.as_view(), name='job'),

                       url(r'^job/(?P<pk>\d+)/(?P<type_name>\w+)/$',
                           type_detail, name = 'type_detail'),

                       url(r'^type_plot/(?P<pk>\d+)/(?P<type_name>\w+)/$', 
                           type_plot, name = 'type_plot'),

                       url(r'^master_plot/(?P<pk>\d+)/$', 
                           master_plot, name = 'master_plot'),

                       url(r'^date_summary/(?P<date>\d{4}-\d{2}-\d{2})/$', 
                           date_summary, name = 'date_summary' ),

                       url(r'^user_summary/(?P<user>\d+)/$', 
                           user_summary, name = 'user_summary' ),

                       url(r'^user/(?P<user>\d+)/$',
                           user_view, name='user_view'),


                       url(r'^search/$',search, name='search'),
                       url(r'^search/job/(?P<pk>\d+)/$', JobDetailView.as_view()),
)
