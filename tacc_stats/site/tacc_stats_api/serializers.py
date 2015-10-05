from rest_framework import serializers
from tacc_stats.site.machine.models import Job, TestInfo
from tacc_stats.site.machine import views as machineViews


class JobSerializer(serializers.HyperlinkedModelSerializer):
    gig_ebw = serializers.FloatField(source='GigEBW')
    vec_percent = serializers.FloatField(source='VecPercent')
    load_all = serializers.IntegerField(source='Load_All')
    load_l1hits = serializers.IntegerField(source='Load_L1Hits')
    load_l2hits = serializers.IntegerField(source='Load_L2Hits')
    load_llchits = serializers.IntegerField(source='Load_LLCHits')
    cpu_usage = serializers.FloatField(source='CPU_Usage')
    mic_usage = serializers.FloatField(source='MIC_Usage')
    class Meta:
        model = Job
        fields = ('id', 'uid', 'project', 'start_time','end_time','run_time', 'requested_time',
            'queue', 'queue_time', 'status', 'nodes', 'cores', 'wayness', 'date', 'user', 'cpi',
            'cpld', 'mbw', 'cat', 'idle', 'mem', 'packetrate', 'packetsize', 'gig_ebw', 'flops', 
            'vec_percent', 'load_all', 'load_l1hits', 'load_l2hits', 'load_llchits', 'cpu_usage', 
            'mic_usage')

class JobDetailSerializer(serializers.HyperlinkedModelSerializer):
    gig_ebw = serializers.FloatField(source='GigEBW')
    vec_percent = serializers.FloatField(source='VecPercent')
    load_all = serializers.IntegerField(source='Load_All')
    load_l1hits = serializers.IntegerField(source='Load_L1Hits')
    load_l2hits = serializers.IntegerField(source='Load_L2Hits')
    load_llchits = serializers.IntegerField(source='Load_LLCHits')
    cpu_usage = serializers.FloatField(source='CPU_Usage')
    mic_usage = serializers.FloatField(source='MIC_Usage')
    master_plot = serializers.SerializerMethodField()
    sys_plot = serializers.SerializerMethodField()
    heat_map = serializers.SerializerMethodField()
    type_list = serializers.SerializerMethodField()

    def get_master_plot(self, obj):
        return machineViews.master_plot(None, 'wrangler', obj.id, view_type='api')

    def get_sys_plot(self, obj):
        return machineViews.sys_plot(None, obj.id, view_type='api')

    def get_heat_map(self, obj):
        return machineViews.heat_map(None, 'wrangler', obj.id, view_type='api')

    def get_type_list(self, obj):
        return machineViews.type_list('wrangler', obj.id)

    class Meta:
        model = Job
        fields = ('id', 'uid', 'project', 'start_time','end_time','run_time', 'requested_time',
         'queue', 'queue_time', 'status', 'nodes', 'cores', 'wayness', 'date', 'user', 'cpi', 
         'cpld', 'mbw', 'cat', 'idle', 'mem', 'packetrate', 'packetsize', 'load_all', 'gig_ebw', 
         'flops', 'vec_percent', 'load_l1hits', 'load_l2hits', 'load_llchits', 'cpu_usage', 
         'mic_usage', 'master_plot', 'sys_plot', 'heat_map', 'type_list')

class TestInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestInfo
        exclude = ('id')