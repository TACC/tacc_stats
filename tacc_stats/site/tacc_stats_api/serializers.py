from django.contrib.auth.models import User, Group
from rest_framework import serializers
from tacc_stats.site.machine.models import Job
from tacc_stats.site.machine import apiviews

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')

class JobSerializer(serializers.HyperlinkedModelSerializer):
    gig_ebw = serializers.CharField(source='GigEBW')
    vec_percent = serializers.CharField(source='VecPercent')
    class Meta:
        model = Job
        fields = ('id', 'project', 'start_time','end_time','run_time','queue','status','date','user','cpi','mbw','idle','cat','mem','packetrate','packetsize','gig_ebw','flops','vec_percent',)

class JobDetailSerializer(serializers.HyperlinkedModelSerializer):
    master_plot = serializers.SerializerMethodField("get_master_plot")
    heat_map = serializers.SerializerMethodField("get_heat_map")
    sys_plot = serializers.SerializerMethodField("get_sys_plot")
    type_list = serializers.SerializerMethodField("get_type_list")
    gig_ebw = serializers.CharField(source='GigEBW')
    vec_percent = serializers.CharField(source='VecPercent')
    def get_master_plot(self,obj):
        return apiviews.master_plot(None, obj.id)

    def get_heat_map(self,obj):
        return apiviews.heat_map(None, obj.id)

    def get_sys_plot(self,obj):
        return apiviews.sys_plot(None, obj.id)

    def get_type_list(self, obj):
        return apiviews.type_list(obj.id)

    class Meta:
        model = Job
        fields = ('id','uid', 'project', 'start_time','end_time','run_time','queue_time','queue','name','status','nodes','cores','wayness','path','date','user','exe','threads','cpi','mbw','idle','cat','mem','packetrate','packetsize','gig_ebw','flops','vec_percent','master_plot','heat_map','sys_plot','type_list')
