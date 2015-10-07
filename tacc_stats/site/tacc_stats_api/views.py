from django.contrib.auth.models import User, Group
from django.db.models import Q
from rest_framework import viewsets
from rest_framework_extensions.mixins import PaginateByMaxMixin
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from serializers import JobSerializer, JobDetailSerializer, TestInfoSerializer
from tacc_stats.site.machine.models import Job, TestInfo
from tacc_stats.site.machine import views as machineViews
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, detail_route, renderer_classes
from rest_framework import status
from rest_framework.views import APIView
from renderers import TACCJSONRenderer
import logging

logger = logging.getLogger('default')

def permission_denied_handler(request):
    from django.http import HttpResponse
    return HttpResponse('You don\'t have required permission!')

class ThresholdList(APIView):
    renderer_classes = (TACCJSONRenderer,)

    def get(self, request, resource_name, format=None):
        """
        Gives job flag threshold list set on a resource.
        ---
        # YAML (must be separated by `---`)
        serializer: TestInfoSerializer
        omit_serializer: false
        parameters_strategy: merge
        parameters:
        - name: resource_name
          required: true
          type: string
          enum:
            - stampede
            - lonestar
            - maverick
            - wrangler
          paramType: path
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """

        queryset = TestInfo.objects.all()
        context = dict(request=request)
        serializer = TestInfoSerializer(queryset, many=True, context=context)
        return Response(serializer.data)

    def post(self, request, resource_name, format=None):
        """
        Creates new job flag threshold on a resource.
        ---
        serializer: TestInfoSerializer
        omit_serializer: false
        parameters_strategy: merge
        parameters:
        - name: threshold
          required: true
          type: number
          format: double
          paramType: form
        - name: resource_name
          required: true
          type: string
          enum:
            - stampede
            - lonestar
            - maverick
            - wrangler
          paramType: path
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """

        queryset = TestInfo.objects.all()
        context = dict(request=request)
        serializer = TestInfoSerializer(queryset, many=True, context=context)
        return Response(serializer.data)

class ThresholdDetail(APIView):

    @renderer_classes((TACCJSONRenderer,))
    def put(self, request, pk, resource_name, format=None):
        """
        Updates job flag threshold set on a resource.
        ---
        serializer: TestInfoSerializer
        omit_serializer: false
        parameters_strategy: merge
        parameters:
        - name: threshold
          required: true
          type: number
          format: double
          paramType: form
        - name: resource_name
          required: true
          type: string
          enum:
            - stampede
            - lonestar
            - maverick
            - wrangler
          paramType: path
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """

        queryset = TestInfo.objects.all()
        context = dict(request=request)
        serializer = TestInfoSerializer(queryset, many=True, context=context)
        return Response(serializer.data)

    @renderer_classes((TACCJSONRenderer,))
    def delete(self, request, pk, resource_name, format=None):
        """
        Deletes a job flag threshold set on a resource.
        ---
        serializer: TestInfoSerializer
        omit_serializer: false
        parameters_strategy: merge
        parameters:
        - name: resource_name
          required: true
          type: string
          enum:
            - stampede
            - lonestar
            - maverick
            - wrangler
          paramType: path
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """

        queryset = TestInfo.objects.all()
        context = dict(request=request)
        serializer = TestInfoSerializer(queryset, many=True, context=context)
        return Response(serializer.data)


class JobViewSet(viewsets.ReadOnlyModelViewSet):
    # this serializer below is overridden by method level serializers, it is here to shut up an assertion error
    serializer_class = JobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    renderer_classes = (TACCJSONRenderer,)
    def list(self, request, resource_name):
        """
        Returns job list on a resource filtered by the params below. Recommended to use 
        as many filters as possible to narrow the search.
        ---
        serializer: JobSerializer
        omit_serializer: false
        parameters_strategy: merge
        parameters:
        - name: resource_name
          description: resource name
          required: true
          type: string
          enum:
            - stampede
            - lonestar
            - maverick
            - wrangler
          paramType: path
        - name: user
          description: Owner of the job
          required: false
          type: string
          paramType: query
        - name: project
          description: ID of the corresponding project
          type: integer
          format: int64
          required: false
          paramType: query
        - name: id
          description: ID of the job
          required: false
          type: integer
          format: int64
          paramType: query
        - name: uid
          description: uid of the job
          required: false
          type: integer
          format: int64
          paramType: query
        - name: start_time
          description: Datetime when the job started e.g. 2015-10-01T13:46:59Z
          required: false
          type: string
          format: date-time
          paramType: query
        - name: end_time
          description: Datetime when the job ended e.g. 2015-10-01T13:46:59Z
          required: false
          type: string
          format: date-time
          paramType: query
        - name: queue
          description: Queue name this job is in.
          required: false
          type: string
          paramType: query
        - name: status
          description: Status of this job
          required: false
          type: string
          enum:
            - queued
            - running
            - completed
          paramType: query
        responseMessages:
            - code: 401
              message: Not authenticated
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
        context = dict(resource_name=resource_name)
        serializer = JobSerializer(queryset, many=True, context=context)
        return Response(serializer.data)

    def retrieve(self, request, resource_name, pk=None):
        """
        Returns a job run on a resource by job id.
        ---
        serializer: JobDetailSerializer
        omit_serializer: false
        parameters_strategy: merge
        parameters:
        - name: resource_name
          description: resource name
          required: true
          type: string
          enum:
            - stampede
            - lonestar
            - maverick
            - wrangler
          paramType: path
        responseMessages:
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """
        job = Job.objects.using(resource_name).get(pk=pk)
        context = dict(resource_name=resource_name)
        serializer = JobDetailSerializer(job, context=context)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def type_info(self, request, pk=None):
        """
        Returns type info for a job run on a resource.
        ---
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
        - name: resource_name
          description: resource name
          required: true
          type: string
          enum:
            - stampede
            - lonestar
            - maverick
            - wrangler
          paramType: path
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

def _getFlags():
  thresholds = {}
  for thresholdInstance in TestInfo.objects.all():
    thresholds[thresholdInstance.field_name] = {
        'value': thresholdInstance.threshold,
        'comparator': thresholdInstance.comparator
    }
  return thresholds

def _getFilter(key, comparator):
  result = ''
  if (comparator == '>'):
    result = key + '__' + 'gte'
  elif (comparator == '<'):
    result = key + '__' + 'lte'
  return result


@api_view(['GET'])
@renderer_classes((TACCJSONRenderer,))
def flagged_jobs(request, resource_name):
    """
    Returns flagged jobs run on a resource filtered by the params below.
    ---
    type:
      cpu_usage:
        required: true
        type: array
      mem_usage:
        required: true
        type: array
      mic_usage:
        required: true
        type: array
      mem_bw:
        required: true
        type: array
      catastrophe:
        required: true
        type: array
      gig_ebw:
        required: true
        type: array
      load_all:
        required: true
        type: array
      metadata_rate:
        required: true
        type: array
      load_llc_hits:
        required: true
        type: array
      high_cpi:
        required: true
        type: array
      idle:
        required: true
        type: array
      load_l1_hits:
        required: true
        type: array
      load_l2_hits:
        required: true
        type: array
      low_flops:
        required: true
        type: array
      packet_rate:
        required: true
        type: array
      packet_size:
        required: true
        type: array
      vec_percent:
        required: true
        type: array
      high_cpld:
        required: true
        type: array
    omit_serializer: true
    parameters_strategy: merge
    parameters:
    - name: resource_name
      description: resource name
      required: true
      type: string
      enum:
        - stampede
        - lonestar
        - maverick
        - wrangler
      paramType: path
    - name: user
      description: Owner of the job
      required: false
      type: string
      paramType: query
    - name: project
      description: ID of the corresponding project
      type: integer
      format: int64
      required: false
      paramType: query
    - name: id
      description: ID of the job
      required: false
      type: integer
      format: int64
      paramType: query
    - name: uid
      description: uid of the job
      required: false
      type: integer
      format: int64
      paramType: query
    - name: start_time
      description: Datetime when the job started e.g. 2015-10-01T13:46:59Z
      required: false
      type: string
      format: date-time
      paramType: query
    - name: end_time
      description: Datetime when the job ended e.g. 2015-10-01T13:46:59Z
      required: false
      type: string
      format: date-time
      paramType: query
    - name: queue
      description: Queue name this job is in.
      required: false
      type: string
      paramType: query
    - name: status
      description: Status of this job
      required: false
      type: string
      enum:
        - queued
        - running
        - completed
      paramType: query
    responseMessages:
        - code: 401
          message: Not authenticated
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

    if field.has_key('date'): 
        date = field['date'].split('-')
        if len(date) == 2:
            field['date__year'] = date[0]
            field['date__month'] = date[1]
            del field['date']
    logger.debug('Request params: %s', field)
    job_list = Job.objects.filter(**field).order_by(order_key)
    flags = _getFlags()
    data={}
    catfilter = _getFilter('cat', flags.get('cat').get('comparator'))
    data['catastrophe']  = job_list.filter(Q(**{catfilter: flags.get('cat').get('value')}) | Q(cat__gte = 1000)).exclude(cat = float('nan')).values_list('id', flat=True)
    completed_list = job_list.exclude(status__in=['CANCELLED','FAILED']).order_by('-id')
    if len(completed_list) > 0:
        loadAllFilter = _getFilter('Load_All', flags.get('Load_All').get('comparator'))
        data['load_all'] = completed_list.filter(**{loadAllFilter: flags.get('Load_All').get('value')}).values_list('id', flat=True)
        loadLLCHitsFilter = _getFilter('Load_LLCHits', flags.get('Load_LLCHits').get('comparator'))
        data['load_llc_hits'] = completed_list.filter(**{loadLLCHitsFilter: flags.get('Load_LLCHits').get('value')}).values_list('id', flat=True)
        loadL1HitsFilter = _getFilter('Load_L1Hits', flags.get('Load_L1Hits').get('comparator'))
        data['load_l1_hits'] = completed_list.filter(**{loadL1HitsFilter: flags.get('Load_L1Hits').get('value')}).values_list('id', flat=True)
        loadL2HitsFilter = _getFilter('Load_L2Hits', flags.get('Load_L2Hits').get('comparator'))
        data['load_l2_hits'] = completed_list.filter(**{loadL2HitsFilter: flags.get('Load_L2Hits').get('value')}).values_list('id', flat=True)
        MetaDataRateFilter = _getFilter('MetaDataRate', flags.get('MetaDataRate').get('comparator'))
        data['metadata_rate'] = completed_list.filter(**{MetaDataRateFilter: flags.get('MetaDataRate').get('value')}).values_list('id', flat=True)
        idleFilter = _getFilter('idle', flags.get('idle').get('comparator'))
        data['idle'] = completed_list.filter(**{idleFilter: flags.get('idle').get('value')}).values_list('id', flat=True)
        memFilter = _getFilter('mem', flags.get('mem').get('comparator'))
        data['mem_usage'] = completed_list.filter(**{memFilter: flags.get('mem').get('value'), 'queue': 'largemem'}).values_list('id', flat=True)
        CPUUsageFilter = _getFilter('CPU_Usage', flags.get('CPU_Usage').get('comparator'))
        data['cpu_usage'] = completed_list.filter(**{CPUUsageFilter: flags.get('CPU_Usage').get('value')}).values_list('id', flat=True)
        MICUsageFilter = _getFilter('MIC_Usage', flags.get('MIC_Usage').get('comparator'))
        data['mic_usage'] = completed_list.filter(**{MICUsageFilter: flags.get('MIC_Usage').get('value')}).values_list('id', flat=True)
        cpiFilter = _getFilter('cpi', flags.get('cpi').get('comparator'))
        data['high_cpi']  = completed_list.exclude(cpi = float('nan')).filter(**{cpiFilter: flags.get('cpi').get('value')}).values_list('id', flat=True)
        cpldFilter = _getFilter('cpld', flags.get('cpld').get('comparator'))
        data['high_cpld']  = completed_list.exclude(cpld = float('nan')).filter(**{cpldFilter: flags.get('cpld').get('value')}).values_list('id', flat=True)
        gigEBWFilter = _getFilter('GigEBW', flags.get('GigEBW').get('comparator'))
        data['gig_ebw']  = completed_list.exclude(GigEBW = float('nan')).filter(**{gigEBWFilter: flags.get('GigEBW').get('value')}).values_list('id', flat=True)
        vecPercentFilter = _getFilter('VecPercent', flags.get('VecPercent').get('comparator'))
        data['vec_percent']  = completed_list.exclude(VecPercent = float('nan')).filter(**{vecPercentFilter: flags.get('VecPercent').get('value')}).values_list('id', flat=True)
        flopsFilter = _getFilter('flops', flags.get('flops').get('comparator'))
        data['low_flops'] = completed_list.filter(**{flopsFilter: flags.get('flops').get('value')}).values_list('id', flat=True)
        packetRateFilter = _getFilter('packetrate', flags.get('packetrate').get('comparator'))
        data['packet_rate'] = completed_list.filter(**{packetRateFilter: flags.get('packetrate').get('value')}).values_list('id', flat=True)
        packetSizeFilter = _getFilter('packetsize', flags.get('packetsize').get('comparator'))
        data['packet_size'] = completed_list.filter(**{packetSizeFilter: flags.get('packetsize').get('value')}).values_list('id', flat=True)
        mbwFilter = _getFilter('mbw', flags.get('mbw').get('comparator'))
        data['mem_bw'] = completed_list.filter(**{mbwFilter: flags.get('mbw').get('value')}).values_list('id', flat=True)
    return Response(data)

@api_view(['GET'])
@renderer_classes((TACCJSONRenderer,))
def characteristics_plot(request, resource_name):
    """
    Returns job characteristics base64 encoded plot for job list filtered by the params below.
    ---
    omit_serializer: true
    parameters_strategy: merge
    parameters:
    - name: resource_name
      description: resource name
      required: true
      type: string
      enum:
        - stampede
        - lonestar
        - maverick
        - wrangler
      paramType: path
    - name: user
      description: Owner of the job
      required: false
      type: string
      paramType: query
    - name: project
      description: ID of the corresponding project
      type: integer
      format: int64
      required: false
      paramType: query
    - name: id
      description: ID of the job
      required: false
      type: integer
      format: int64
      paramType: query
    - name: uid
      description: uid of the job
      required: false
      type: integer
      format: int64
      paramType: query
    - name: start_time
      description: Datetime when the job started e.g. 2015-10-01T13:46:59Z
      required: false
      type: string
      format: date-time
      paramType: query
    - name: end_time
      description: Datetime when the job ended e.g. 2015-10-01T13:46:59Z
      required: false
      type: string
      format: date-time
      paramType: query
    - name: queue
      description: Queue name this job is in.
      required: false
      type: string
      paramType: query
    - name: status
      description: Status of this job
      required: false
      type: string
      enum:
        - queued
        - running
        - completed
      paramType: query
    responseMessages:
        - code: 401
          message: Not authenticated
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
    queryset = Job.objects.filter(**field).order_by(order_key)
    logger.debug('Query: %s', queryset.query)
    return machineViews.hist_summary(queryset, view_type='api')
