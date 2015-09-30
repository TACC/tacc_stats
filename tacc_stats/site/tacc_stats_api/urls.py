from django.conf.urls import patterns, url
from rest_framework import routers
from django.views.generic import DetailView, ListView
from tacc_stats.site.tacc_stats_api.views import *

api_router = routers.DefaultRouter()

api_router.register(r'(?P<resource_name>(stampede|lonestar|maverick|wrangler))/flagged-jobs/user', JobViewSet, 'user_flagged_jobs')

api_router.register(r'stampede/flagged-jobs/project', JobViewSet, 'stampede_project_flagged_jobs')
api_router.register(r'lonestar/flagged-jobs/project', JobViewSet, 'lonestar_project_flagged_jobs')
api_router.register(r'maverick/flagged-jobs/project', JobViewSet, 'maverick_project_flagged_jobs')
api_router.register(r'wrangler/flagged-jobs/project', JobViewSet, 'wrangler_project_flagged_jobs')

api_router.register(r'stampede/thresholds', get_thresholds, 'stampede_thresholds')
api_router.register(r'lonestar/thresholds', get_thresholds, 'lonestar_thresholds')
api_router.register(r'maverick/thresholds', get_thresholds, 'maverick_thresholds')
api_router.register(r'wrangler/thresholds', get_thresholds, 'wrangler_thresholds')

