import django_filters
from tacc_stats.site.machine.models import Job
from serializers import JobSerializer
from rest_framework import filters

class JobFilter(django_filters.FilterSet):
    start_time_from = django_filters.IsoDateTimeFilter(name="start_time", lookup_type='gte')
    start_time_to = django_filters.IsoDateTimeFilter(name="start_time", lookup_type='lte')
    end_time_from = django_filters.IsoDateTimeFilter(name="end_time", lookup_type='gte')
    end_time_to = django_filters.IsoDateTimeFilter(name="end_time", lookup_type='lte')
    min_run_time = django_filters.NumberFilter(name="min_run_time", lookup_type='gte')
    max_run_time = django_filters.NumberFilter(name="max_run_time", lookup_type='lte')
    min_requested_time = django_filters.NumberFilter(name="min_requested_time", lookup_type='gte')
    max_requested_time = django_filters.NumberFilter(name="max_requested_time", lookup_type='lte')
    min_queue_time = django_filters.NumberFilter(name="min_queue_time", lookup_type='gte')
    max_queue_time = django_filters.NumberFilter(name="max_queue_time", lookup_type='lte')
    min_nodes = django_filters.NumberFilter(name="min_nodes", lookup_type='gte')
    max_nodes = django_filters.NumberFilter(name="max_nodes", lookup_type='lte')
    min_cores = django_filters.NumberFilter(name="min_cores", lookup_type='gte')
    max_cores = django_filters.NumberFilter(name="max_cores", lookup_type='lte')
    
    class Meta:
        model = Job
        fields = ['id', 'uid', 'user', 'project', 'queue', 'status', 'date',  'start_time_from', 'start_time_to', 'end_time_from', 'end_time_to',
         'max_run_time', 'min_run_time', 'max_requested_time', 'min_requested_time', 'max_queue_time', 'min_queue_time', 'max_nodes', 'min_nodes',
         'max_cores', 'min_cores']