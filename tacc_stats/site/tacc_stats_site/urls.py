from django.conf.urls import include, url
from django.views.static import serve
import settings
from django.contrib import admin
from tacc_stats.site.machine.views import dates, login, logout, login_oauth, agave_oauth_callback
from tacc_stats.site.machine import urls

admin.autodiscover()

urlpatterns = [
    url(r'^$', dates, name='dates'),
    url(r'^login/$', login_oauth, name='login'),
    url(r'^agave_oauth_callback/$', agave_oauth_callback, name='agave_oauth_callback'),
    url(r'^logout/$', logout, name='logout'),
    url(r'^machine/', include(urls, namespace="machine"), name='machine'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^media/(?P<path>.*)$', serve,
        {'document_root': settings.MEDIA_ROOT}),                       
]
