from django.conf.urls import patterns, include, url
import settings
from django.contrib import admin
from django.contrib.auth.models import User
from tacc_stats.site.tacc_stats_site.views import *
from rest_framework import routers, serializers, viewsets
from django.views.generic import DetailView, ListView
from tacc_stats.site.tacc_stats_api.views import *
from tacc_stats.site.tacc_stats_api.urls import api_router

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', home, name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}), 
    #url(r'^docs/', include('rest_framework_swagger.urls')),
     #Django Rest API
    url(r'^api/', include(api_router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^(?P<resource_name>(stampede|lonestar|maverick|wrangler))/', include('machine.urls', namespace="machine"), name='machine'),
)
