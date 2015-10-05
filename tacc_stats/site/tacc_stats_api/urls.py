from django.conf.urls import patterns, include, url
from rest_framework import routers
from django.views.generic import DetailView, ListView
from tacc_stats.site.tacc_stats_api.views import *

api_router = routers.DefaultRouter()

api_router.register(r'(?P<resource_name>stampede|lonestar|maverick|wrangler)', JobViewSet, 'jobs')

urlpatterns = patterns('',
                       url(r'^thresholds/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', thresholds, name='thresholds'),
                       url(r'^flagged-jobs/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', flagged_jobs, name='flagged_jobs'),
                       url(r'^characteristics-plot/(?P<resource_name>stampede|lonestar|maverick|wrangler)$', characteristics_plot, name='characteristics_plot'),
                       )