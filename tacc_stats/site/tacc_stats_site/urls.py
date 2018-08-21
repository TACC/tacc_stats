from django.conf.urls import include
from django.urls import path
from django.views.static import serve
from tacc_stats.site.tacc_stats_site import settings
from django.contrib import admin
from tacc_stats.site.machine.views import dates
from tacc_stats.site.machine import urls

admin.autodiscover()
urlpatterns = [
    path(r'', dates, name="dates"),
    path(r'machine/', include(urls, namespace = "machine"), name = "machine"),
    path(r'media/<path>', serve, {'document_root': settings.MEDIA_ROOT}, name = "media"),                       
]
