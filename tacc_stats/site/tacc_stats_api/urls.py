from django.conf.urls import patterns, include, url
from rest_framework import routers
from django.views.generic import DetailView, ListView
from tacc_stats.site.tacc_stats_api.views import *

api_router = routers.DefaultRouter()
api_router.register(r'token', TokenViewSet, 'token')

urlpatterns = patterns('',
                       url(r'^thresholds/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', ThresholdList.as_view()),
                       url(r'^thresholds/(?P<pk>\d+)/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', ThresholdDetail.as_view()),
                       url(r'^flagged-jobs/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', flagged_jobs, name='flagged_jobs'),
                       url(r'^characteristics-plot/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', characteristics_plot, name='characteristics_plot'),
                       url(r'^jobs/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', cache_page(43200)(JobListView.as_view()), name='job_list'),
                       url(r'^jobs/(?P<pk>\d+)/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', job_detail, name='job_detail'),
                       url(r'^jobs/(?P<pk>\d+)/(?P<resource_name>stampede|lonestar|maverick|wrangler)/device-data/(?P<device_name>\w+)$', device_data, name='device_data'),
                       )