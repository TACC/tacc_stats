from django.conf.urls import patterns, include, url
import settings
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'tacc_stats_site.views.home', name='home'),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),                       
    # url(r'^tacc_stats_site/', include('tacc_stats_site.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^lonestar/', include('lonestar.urls', namespace="lonestar"),name='lonestar'),
    url(r'^stampede/', include('stampede.urls', namespace="stampede"),name='stampede'),
    
    url(r'^admin/', include(admin.site.urls)),
)
