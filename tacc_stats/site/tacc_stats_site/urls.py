from django.conf.urls import patterns, include, url
import settings
from django.contrib import admin
from django.contrib.auth.models import User
from tacc_stats.site.tacc_stats_site import views as siteViews
from rest_framework import routers, serializers, viewsets
from django.views.generic import DetailView, ListView
from tacc_stats.site.tacc_stats_api.urls import api_router

#not needed in django 1.7
#admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', siteViews.home, name='home'),
    url(r'^swagger/', include('rest_framework_swagger.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
    url(r'^api/', include(api_router.urls)),
    url(r'^api/', include('tacc_stats_api.urls', namespace='tacc_stats_api')),
    #url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    #url(r'^api-token-auth/', 'rest_framework.authtoken.views.obtain_auth_token'),
    url(r'^(?P<resource_name>(stampede|lonestar|maverick|wrangler))/', include('machine.urls', namespace="machine")),
)
