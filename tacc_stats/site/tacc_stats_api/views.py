from django.contrib.auth.models import User, Group
from django.db.models import Q
from rest_framework import viewsets
from rest_framework_extensions.mixins import PaginateByMaxMixin
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from serializers import JobSerializer, JobDetailSerializer, TestInfoSerializer
from tacc_stats.site.machine.models import Job, TestInfo
from tacc_stats.site.machine import views as machineViews
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, detail_route, renderer_classes
from rest_framework import status
from renderers import TACCJSONRenderer
import logging

logger = logging.getLogger('default')

@api_view(['GET', 'POST', 'PUT'])
@renderer_classes((TACCJSONRenderer,))
def thresholds(request, resource_name):
    queryset = TestInfo.objects.all()
    context = dict(request=request)
    serializer = TestInfoSerializer(queryset, many=True, context=context)
    return Response(serializer.data)

@api_view(['GET'])
@renderer_classes((TACCJSONRenderer,))
def flagged_jobs(request, resource_name):
    field = {}
    for param in request.query_params:
        val = request.query_params.get(param)
        field[param] = val
    order_key = '-id'
    if 'order_key' in field: 
        order_key = field['order_key']
        del field['order_key']

    if field.has_key('date'): 
        date = field['date'].split('-')
        if len(date) == 2:
            field['date__year'] = date[0]
            field['date__month'] = date[1]
            del field['date']
    logger.debug('Request params: %s', field)
    job_list = Job.objects.filter(**field).order_by(order_key)
    data={}
    data['catastrophe']  = job_list.filter(Q(cat__lte = 0.001) | Q(cat__gte = 1000)).exclude(cat = float('nan')).values_list('id', flat=True)
    completed_list = job_list.exclude(status__in=['CANCELLED','FAILED']).order_by('-id')
    if len(completed_list) > 0:
        data['load_all'] = completed_list.filter(Load_All__lte = 10000000).values_list('id', flat=True)
        data['load_llc_hits'] = completed_list.filter(Load_LLCHits__gte = 1.5).values_list('id', flat=True)
        data['load_l1_hits'] = completed_list.filter(Load_L1Hits__gte = 1.5).values_list('id', flat=True)
        data['load_l2_hits'] = completed_list.filter(Load_L2Hits__gte = 1.5).values_list('id', flat=True)
        data['metadata_rate'] = completed_list.filter(MetaDataRate__gte = 100).values_list('id', flat=True)
        data['idle'] = completed_list.filter(idle__gte = 0.99).values_list('id', flat=True)
        data['mem_usage'] = completed_list.filter(mem__lte = 30, queue = 'largemem').values_list('id', flat=True)
        data['cpu_usage'] = completed_list.filter(CPU_Usage__lte = 800).values_list('id', flat=True)
        data['mic_usage'] = completed_list.filter(MIC_Usage__gte = 0).values_list('id', flat=True)
        data['high_cpi']  = completed_list.exclude(cpi = float('nan')).filter(cpi__gte = 1.5).values_list('id', flat=True)
        data['high_cpld']  = completed_list.exclude(cpi = float('nan')).filter(cpld__gte = 1.5).values_list('id', flat=True)
        data['gig_ebw']  = completed_list.exclude(GigEBW = float('nan')).filter(GigEBW__gte = 2**20).values_list('id', flat=True)
        data['vec_percent']  = completed_list.exclude(VecPercent = float('nan')).filter(VecPercent__lte = 0.05).values_list('id', flat=True)
        data['low_flops'] = completed_list.filter(flops__lte = 10).values_list('id', flat=True)
        data['packet_rate'] = completed_list.filter(packetrate__gte = 0).values_list('id', flat=True)
        data['packet_size'] = completed_list.filter(packetsize__gte = 0).values_list('id', flat=True)
        data['mem_bw'] = completed_list.filter(mbw__lte = 1).values_list('id', flat=True)
    return Response(data)

@api_view(['GET'])
@renderer_classes((TACCJSONRenderer,))
def characteristics_plot(request, resource_name):
    field = {}
    for param in request.query_params:
        val = request.query_params.get(param)
        field[param] = val
    order_key = '-id'
    if 'order_key' in field: 
        order_key = field['order_key']
        del field['order_key']
    logger.debug('Request params: %s', field)
    queryset = Job.objects.filter(**field).order_by(order_key)
    logger.debug('Query: %s', queryset.query)
    return machineViews.hist_summary(queryset, view_type='api')

class JobViewSet(viewsets.ReadOnlyModelViewSet):
    #serializer_class = JobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    renderer_classes = (TACCJSONRenderer,)
    def list(self, request, resource_name):
        """
        Returns jobs run on a resource.
        ---
        # YAML (must be separated by `---`)

        serializer: JobSerializer
        omit_serializer: false
        parameters_strategy: replace
        parameters:
        - name: user
          description: Owner of the job
          required: false
          type: string
          paramType: query
        - name: project_id
          description: ID of the corresponding project
          type: string
          required: false
          paramType: query
        - name: job_id
          description: ID of the job
          required: false
          type: string
          paramType: query
        - name: start_time
          description: Datetime when the job started
          required: false
          type: string
          paramType: query
        - name: end_time
          description: Datetime when the job ended
          required: false
          type: string
          paramType: query
        - name: queue
          description: Queue name this job is in.
          required: false
          type: string
          paramType: query
        - name: status
          description: Status of this job ('queued','running','completed')
          required: false
          type: string
          paramType: query
        responseMessages:
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """
        field = {}
        for param in request.query_params:
            val = request.query_params.get(param)
            field[param] = val

        order_key = '-id'
        if 'order_key' in field: 
            order_key = field['order_key']
            del field['order_key']
        logger.debug('Request params: %s', field)
        queryset = Job.objects.using(resource_name).filter(**field).order_by(order_key)
        logger.debug('Query: %s', queryset.query)
        serializer = JobSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, resource_name, pk=None):
        """
        Returns a job run on a resource by job id.
        ---
        # YAML (must be separated by `---`)

        serializer: JobDetailSerializer
        omit_serializer: false
        parameters_strategy: replace
        responseMessages:
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """
        job = Job.objects.using(resource_name).get(pk=pk)
        serializer = JobDetailSerializer(job)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def type_info(self, request, pk=None):
        """
        Returns type info for a job run on Stampede.
        ---
        # YAML (must be separated by `---`)
        type:
          schema:
            required: true
            type: array
          type_name:
            required: true
            type: string
          stats:
            required: true
            type: array
          job_id:
            required: true
            type: integer
          type_plot:
            required: true
            type: string
        omit_serializer: true
        parameters_strategy: merge
        parameters:
        - name: type
          description: type name
          required: true
          type: string
          paramType: query
        responseMessages:
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """
        type_name = request.query_params.get('type', None)
        type_info = apiviews.type_info(pk, type_name)
        return Response(type_info)