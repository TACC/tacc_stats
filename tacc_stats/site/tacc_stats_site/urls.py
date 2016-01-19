from django.conf.urls import patterns, include, url
import settings
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    #url(r'^$', 'tacc_stats_site.views.home', name='home'),
    url(r'^$', 'tacc_stats_site.site.machine.views.dates', name='dates'),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),                       
    url(r'^machine/', include('tacc_stats_site.site.machine.urls', namespace="machine"),name='machine'),
    url(r'^admin/', include(admin.site.urls)),
)
