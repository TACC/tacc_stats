from django.conf.urls import patterns, include, url
from rest_framework import routers
import apiviews
import settings
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

router = routers.DefaultRouter()
router.register(r'users', apiviews.UserViewSet)
router.register(r'groups',apiviews.GroupViewSet)
router.register(r'^jobs(?P<user>[a-zA-Z0-9_]+)/$',apiviews.UserJobs.as_view(),'job-list')
#router.register(r'^jobs',apiviews.JobsViewSet)

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
    
    #Django Rest API
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
)
