from django.conf.urls import patterns, include, url
import settings
from django.contrib import admin
from tacc_stats.site.tacc_stats_site.views import *
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', home, name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}), 
    url(r'^(?P<resource_name>(stampede|lonestar|maverick|wrangler))/', include('machine.urls', namespace="machine"),name='machine'),
)
