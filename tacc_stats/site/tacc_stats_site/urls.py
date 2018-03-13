from django.conf.urls import include, url
from django.views.static import serve
import settings
from django.contrib import admin
from tacc_stats.site.machine.views import dates, login, logout
from tacc_stats.site.machine import urls

admin.autodiscover()

urlpatterns = [
    url(r'^$', dates, name='dates'),
    url(r'^login/$', login, name='login'),
    url(r'^logout/$', logout, name='logout'),
    url(r'^machine/', include(urls, namespace="machine"), name='machine'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^media/(?P<path>.*)$', serve,
        {'document_root': settings.MEDIA_ROOT}),                       
]
