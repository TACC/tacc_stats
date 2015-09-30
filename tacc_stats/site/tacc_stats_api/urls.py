from django.conf.urls import patterns, url
from rest_framework import routers
from django.views.generic import DetailView, ListView
from tacc_stats.site.tacc_stats_api.views import *

api_router = routers.DefaultRouter()

api_router.register(r'(?P<resource_name>(stampede|lonestar|maverick|wrangler))/flagged-jobs/user', JobViewSet, 'user_flagged_jobs')
# Note I: explicitly mentioning each resource so that the api web interface picks em up, 
#requests never get to these routes below as they are handled by the above route declaration.
api_router.register(r'stampede/flagged-jobs/user', JobViewSet, 'user_flagged_jobs-stampede')
api_router.register(r'lonestar/flagged-jobs/user', JobViewSet, 'user_flagged_jobs-lonestar')
api_router.register(r'maverick/flagged-jobs/user', JobViewSet, 'user_flagged_jobs-maverick')
api_router.register(r'wrangler/flagged-jobs/user', JobViewSet, 'user_flagged_jobs-wrangler')

api_router.register(r'(?P<resource_name>(stampede|lonestar|maverick|wrangler))/flagged-jobs/project', JobViewSet, 'project_flagged_jobs')
# read Note I above
api_router.register(r'stampede/flagged-jobs/project', JobViewSet, 'project_flagged_jobs-stampede')
api_router.register(r'lonestar/flagged-jobs/project', JobViewSet, 'project_flagged_jobs-lonestar')
api_router.register(r'maverick/flagged-jobs/project', JobViewSet, 'project_flagged_jobs-maverick')
api_router.register(r'wrangler/flagged-jobs/project', JobViewSet, 'project_flagged_jobs-wrangler')

api_router.register(r'(?P<resource_name>(stampede|lonestar|maverick|wrangler))/thresholds', JobViewSet, 'thresholds')
# read Note I above
api_router.register(r'stampede/thresholds', JobViewSet, 'thresholds-stampede')
api_router.register(r'lonestar/thresholds', JobViewSet, 'thresholds-lonestar')
api_router.register(r'maverick/thresholds', JobViewSet, 'thresholds-maverick')
api_router.register(r'wrangler/thresholds', JobViewSet, 'thresholds-wrangler' )