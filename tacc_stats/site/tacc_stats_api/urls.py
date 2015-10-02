from django.conf.urls import patterns, url
from rest_framework import routers
from django.views.generic import DetailView, ListView
from tacc_stats.site.tacc_stats_api.views import *

api_router = routers.DefaultRouter()

api_router.register(r'(?P<resource_name>(stampede|lonestar|maverick|wrangler))', JobViewSet, 'jobs')
# read Note I above:
api_router.register(r'stampede', JobViewSet, 'jobs_stampede')
api_router.register(r'lonestar', JobViewSet, 'jobs_lonestar')
api_router.register(r'maverick', JobViewSet, 'jobs_maverick')
api_router.register(r'wrangler', JobViewSet, 'jobs_wrangler')


urlpatterns = patterns('',
                       #url(r'^$', api_root, name='api_root'),
                       url(r'^thresholds/(?P<resource_name>(stampede|lonestar|maverick|wrangler))$', thresholds, name='thresholds'),
                       url(r'^flagged-jobs/(?P<resource_name>(stampede|lonestar|maverick|wrangler))$', flagged_jobs, name='flagged_jobs'),
                       url(r'^characteristics-plot/(?P<resource_name>(stampede|lonestar|maverick|wrangler))$', characteristics_plot, name='characteristics_plot'),
                       )

#api_router.register(r'^characteristics-plot/(?P<resource_name>(stampede|lonestar|maverick|wrangler))$', 'apiView.characteristics_plot', name='characteristics_plot'),
# Note I: explicitly mentioning each resource so that the api web interface picks em up, 
# requests never get to the resource specific 4 routes below as they are handled by the above route declaration.
# api_router.register(r'characteristics-plot/stampede', apiView.characteristics_plot, 'characteristics_plot_stampede')
# api_router.register(r'characteristics-plot/lonestar', apiView.characteristics_plot, 'characteristics_plot_lonestar')
# api_router.register(r'characteristics-plot/maverick', apiView.characteristics_plot, 'characteristics_plot_maverick')
# api_router.register(r'characteristics-plot/wrangler', apiView.characteristics_plot, 'characteristics_plot_wrangler')

# api_router.register(r'flagged-jobs/(?P<resource_name>(stampede|lonestar|maverick|wrangler))', 'apiView.flagged_jobs', 'flagged_jobs')
# # read Note I above:
# api_router.register(r'flagged-jobs/stampede', apiView.flagged_jobs, 'flagged_jobs_stampede')
# api_router.register(r'flagged-jobs/lonestar', apiView.flagged_jobs, 'flagged_jobs_lonestar')
# api_router.register(r'flagged-jobs/maverick', apiView.flagged_jobs, 'flagged_jobs_maverick')
# api_router.register(r'flagged-jobs/wrangler', apiView.flagged_jobs, 'flagged_jobs_wrangler')