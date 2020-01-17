from django.conf.urls import url
from django.urls import path
from django.views.generic import DetailView, ListView
from tacc_stats.site.machine.models import Job
from tacc_stats.site.machine.views import *

app_name = "tacc_stats"

urlpatterns = [
                       path('',dates, name='dates'),
                       path('job/<pk>/',
                           JobDetailView.as_view(), name='job'),
                       path('job/<pk>/<type_name>/',
                           type_detail, name = 'type_detail'),
                       path('proc/<pk>/<proc_name>/',
                           proc_detail, name = 'proc_detail'),
                       path('date/<date>', 
                           index, name='date_view'),
                       path('uid/<uid>/',
                           index, name='uid_view'),
                       path('user/<user>/',
                           index, name='user_view'),
                       path('project/<project>/',
                           index, name='project_view'),
                       path('exe/<exe__icontains>)/',
                           index, name='exe_view'),                       
                       path('search/',search, name='search'),
]

