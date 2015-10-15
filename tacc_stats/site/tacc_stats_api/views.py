from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import ModelForm
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters, generics
from rest_framework.renderers import JSONRenderer
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import api_view, list_route, detail_route, renderer_classes, authentication_classes, permission_classes
from rest_framework.views import APIView
from tacc_stats_api.authentication import CustomTokenAuthentication
from tacc_stats_api.permissions import IsAuthenticatedOrAdmin
from rest_framework.permissions import IsAuthenticated
from serializers import JobSerializer, JobDetailSerializer, TestInfoSerializer, TokenSerializer
from tacc_stats.site.machine.models import Job, TestInfo
from tacc_stats_api.models import Token
from tacc_stats_api.filters import JobFilter
from tacc_stats.site.machine import views as machineViews
from django.http import HttpResponse, Http404
from renderers import TACCJSONRenderer
from django.views.decorators.cache import cache_page
import django_filters
import logging

logger = logging.getLogger('default')

def permission_denied_handler(request):
    from django.http import HttpResponse
    return HttpResponse('You don\'t have required permission!')

class ThresholdList(APIView):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticatedOrAdmin,)

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
        """

        queryset = TestInfo.objects.all()
        context = dict(request=request)
        serializer = TestInfoSerializer(queryset, many=True, context=context)
        logger.debug('List of threshold successfully fetched from database: %s', resource_name)
        return Response({'status': 'success', 'message': '', 'result': serializer.data})
    
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
        """
        logger.debug('Creating new threshold by user: %s, with data: %s, on database: %s', request.user.username, request.data, resource_name)
        serializer = TestInfoSerializer(data=request.data)
        if serializer.is_valid():
          new_instance = serializer.save()
          logger.debug('Threshold successfully created.')
          return Response({'status': 'success', 'message': '', 'result': serializer.data}, status=status.HTTP_201_CREATED)
        else:
          logger.debug('Error creating threshold. %s', serializer.errors)
          return Response({'status': 'error', 'message': 'Error creating this threshold', 'result': serializer.errors.as_json()}, status=status.HTTP_400_BAD_REQUEST)

class ThresholdDetail(APIView):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticatedOrAdmin,)
    
    def get(self, request, pk, resource_name, format=None):
        """
        Retrieves a job flag threshold set on a resource.
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
        """
        
        instance = get_object_or_404(TestInfo, pk=pk)
        serializer = TestInfoSerializer(instance)
        logger.debug('Threshold successfully fetched from database: %s', resource_name)
        return Response({'status': 'success', 'message': '', 'result': serializer.data})
    
    # was unable to use PUT for update because of empty request.data object received
    def post(self, request, pk, resource_name, format=None):
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
        """
        instance = get_object_or_404(TestInfo, pk=pk)
        logger.debug('Requested threshold found in database: %s', resource_name)
        logger.debug('Updating threshold by user: %s, with data: %s', request.user.username, request.data)
        serializer = TestInfoSerializer(instance, data=request.data)
        if serializer.is_valid():
          instance = serializer.save()
          logger.debug('Threshold successfully updated.')
          return Response({'status': 'success', 'message': '', 'result': serializer.data})
        else:
          logger.debug('Error updating threshold. %s', serializer.errors)
          return Response({'status': 'error', 'message': 'Error creating this threshold', 'result': serializer.errors.as_json()}, status=status.HTTP_400_BAD_REQUEST)

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
        """

        instance = get_object_or_404(TestInfo, pk=pk)
        logger.debug('Requested threshold found in database: %s', resource_name)
        logger.debug('Deleting threshold %s by user: %s', instance.test_name, request.user.username)
        instance.delete()
        logger.debug('Threshold successfully deleted.')
        return Response(status=status.HTTP_204_NO_CONTENT)

class TokenViewSet(viewsets.ViewSet):
    renderer_classes = (TACCJSONRenderer,)
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = TokenSerializer
    
    def list(self, request):
        """
        Retrieves/creates token for the user after authenticating via TAS.
        ---
        serializer: TokenSerializer
        omit_serializer: false
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
        """
        username = request.user.username
        logger.debug('Token requested for username: %s', username)
        try:
            token = Token.objects.using('stampede').get(user=request.user)
            logger.debug('Token found.')

        except Token.DoesNotExist:
            logger.debug('Token does not exist. Creating one...')
            token = Token(
              user = request.user
              )
            token.save(using='stampede')
            logger.debug('Token successfully created in stampede_db.')
        serializer = self.serializer_class(token)
        return Response(serializer.data)
    
    @list_route(methods=['post'])
    def refresh(self, request):
        """
        Refreshes/creates token for the user after authenticating via TAS.
        ---
        serializer: TokenSerializer
        omit_serializer: false
        omit_parameters:
        - form
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
        """
        username = request.user.username
        logger.debug('Token refresh requested for username: %s', username)
        try:
            token = Token.objects.using('stampede').get(user=request.user)
            logger.debug('Existing token found. Deleting...')
            token.delete(using='stampede')
            logger.debug('Current token deleted. Creating new one...')
            token = Token(
              user = request.user
              )
            token.save(using='stampede')
            logger.debug('New token created in stampede_db.')
        except Token.DoesNotExist:
            logger.debug('Token does not exist. Creating one...')
            token = Token(
              user = request.user
              )
            token.save(using='stampede')
            logger.debug('Token successfully created in stampede_db.')
        serializer = self.serializer_class(token)
        return Response(serializer.data)
    
    def destroy(self, request, pk=None):
        """
        Deletes token for the user after authenticating via TAS.
        ---
        serializer: TokenSerializer
        omit_serializer: false
        parameters_strategy: merge
        parameters:
        - name: pk
          description: key
          required: true
          type: string
          paramType: path
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
        """
        username = request.user.username
        logger.debug('Token delete requested for username: %s', username)
        try:
            token = Token.objects.using('stampede').get(user=request.user)
            logger.debug('Token found.')
            token.delete(using='stampede')
            logger.debug('Token successfully deleted from stampede_db.')
            return Response('Successfully deleted.', status=status.HTTP_204_NO_CONTENT)
        except Token.DoesNotExist:
            logger.debug('Token not found.')
            return Response('Error. Token not found.', status=status.HTTP_404_NOT_FOUND)

class JobListView(generics.ListAPIView):
    """
    Returns job list on a resource filtered by the params below. Recommended to use 
    as many filters as possible to narrow the search.
    ---
    GET:
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
          description: owner username
          required: false
          type: string
          paramType: query
        - name: project
          description: project id
          type: integer
          format: int64
          required: false
          paramType: query
        - name: id
          description: job id
          required: false
          type: integer
          format: int64
          paramType: query
        - name: uid
          description: job uid
          required: false
          type: integer
          format: int64
          paramType: query
        - name: date
          description: job date e.g. 2015-10-01
          required: false
          type: string
          format: date
          paramType: query
        - name: start_time_from
          description: earliest start time e.g. 2015-10-01T13:46:59Z
          required: false
          type: string
          format: date-time
          paramType: query
        - name: start_time_to
          description: latest start time
          required: false
          type: string
          format: date-time
          paramType: query
        - name: end_time_from
          description: earliest end time
          required: false
          type: string
          format: date-time
          paramType: query
        - name: end_time_to
          description: latest end time
          required: false
          type: string
          format: date-time
          paramType: query
        - name: queue
          description: queue name.
          required: false
          type: string
          paramType: query
        - name: status
          description: job status
          required: false
          type: string
          enum:
            - queued
            - running
            - completed
          paramType: query
        - name: max_run_time
          description: maximum run time
          required: false
          type: integer
          format: int64
          paramType: query
        - name: min_run_time
          description: minimum run time
          required: false
          type: integer
          format: int64
          paramType: query
        - name: max_queue_time
          description: maximum queue time
          required: false
          type: integer
          format: int64
          paramType: query
        - name: min_queue_time
          description: minimum queue time
          required: false
          type: integer
          format: int64
          paramType: query
        - name: max_requested_time
          description: maximum requested time
          required: false
          type: integer
          format: int64
          paramType: query
        - name: min_requested_time
          description: minimum requested time
          required: false
          type: integer
          format: int64
          paramType: query
        - name: max_nodes
          description: maximum nodes
          required: false
          type: integer
          format: int64
          paramType: query
        - name: min_nodes
          description: minimum nodes
          required: false
          type: integer
          format: int64
          paramType: query
        - name: max_cores
          description: maximum cores
          required: false
          type: integer
          format: int64
          paramType: query
        - name: min_cores
          description: minimum cores
          required: false
          type: integer
          format: int64
          paramType: query
        - name: page
          description: page number
          required: false
          type: integer
          format: int64
          paramType: query
        responseMessages:
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
            - code: 500
              message: Internal Server Error
    """
    serializer_class = JobSerializer
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter,)
    filter_class = JobFilter
    ordering_fields = '__all__'
    ordering = ('id',)
    pagination_class = PageNumberPagination
    queryset = Job.objects.all()

@api_view(['GET'])
@authentication_classes((CustomTokenAuthentication,))
@permission_classes((IsAuthenticated,))    
def job_detail(request, pk, resource_name):
    """
    Returns a job run on a resource by job id.
    ---
    serializer: JobDetailSerializer
    omit_serializer: false
    parameters_strategy: merge
    parameters:
    - name: pk
      description: job id
      required: true
      type: integer
      format: int64
      paramType: path
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
        - code: 401
          message: Not authenticated
        - code: 403
          message: Insufficient rights to call this procedure
        - code: 500
          message: Internal Server Error

    """
    logger.debug('Job detail requested for pk %s on resource %s.', pk, resource_name)
    job = Job.objects.using(resource_name).get(pk=pk)
    context = dict(resource_name=resource_name)
    if job is not None:
      logger.debug('Job found.')
      serializer = JobDetailSerializer(job, context=context)
      logger.debug('Job metadata added.')
      return Response({'status': 'success', 'message': '', 'result': serializer.data})
    else:
      logger.debug('Job not found.')
      return Response({'status': 'error', 'message': 'Not found', 'result': None})

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
@authentication_classes((CustomTokenAuthentication,))
@permission_classes((IsAuthenticated,))
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
      description: job owner
      required: false
      type: string
      paramType: query
    - name: project
      description: project id
      type: integer
      format: int64
      required: false
      paramType: query
    - name: start_time_from
      description: earliest start time e.g. 2015-10-01T13:46:59Z
      required: false
      type: string
      format: date-time
      paramType: query
    - name: start_time_to
      description: latest start time
      required: false
      type: string
      format: date-time
      paramType: query
    - name: end_time_from
      description: earliest end time
      required: false
      type: string
      format: date-time
      paramType: query
    - name: end_time_to
      description: latest end time
      required: false
      type: string
      format: date-time
      paramType: query
    - name: queue
      description: queue name
      required: false
      type: string
      paramType: query
    - name: status
      description: job status
      required: false
      type: string
      enum:
        - queued
        - running
        - completed
      paramType: query
    - name: max_run_time
      description: maximum run time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_run_time
      description: minimum run time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_queue_time
      description: maximum queue time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_queue_time
      description: minimum queue time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_requested_time
      description: maximum requested time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_requested_time
      description: minimum requested time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_nodes
      description: maximum nodes
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_nodes
      description: minimum nodes
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_cores
      description: maximum cores
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_cores
      description: minimum cores
      required: false
      type: integer
      format: int64
      paramType: query
    responseMessages:
        - code: 401
          message: Not authenticated
        - code: 403
          message: Insufficient rights to call this procedure
        - code: 500
          message: Internal Server Error
    """
    logger.debug('Flagged jobs requested by user: %s on %s.', request.user.username, resource_name)
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
    job_list = JobFilter(request.GET, queryset=Job.objects.all()).qs
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
        logger.debug('All thresholds applied.')
    else:
        logger.debug('Empty completed jobs list.')
    return Response({'status': 'success', 'message': '', 'result': data})

@api_view(['GET'])
@authentication_classes((CustomTokenAuthentication,))
@permission_classes((IsAuthenticated,))
@cache_page(60 * 15, cache="default")
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
      description: job owner
      required: false
      type: string
      paramType: query
    - name: project
      description: project id
      type: integer
      format: int64
      required: false
      paramType: query
    - name: id
      description: job id
      required: false
      type: integer
      format: int64
      paramType: query
    - name: uid
      description: job uid
      required: false
      type: integer
      format: int64
      paramType: query
    - name: start_time_from
      description: earliest start time e.g. 2015-10-01T13:46:59Z
      required: false
      type: string
      format: date-time
      paramType: query
    - name: start_time_to
      description: latest start time
      required: false
      type: string
      format: date-time
      paramType: query
    - name: end_time_from
      description: earliest end time
      required: false
      type: string
      format: date-time
      paramType: query
    - name: end_time_to
      description: latest end time
      required: false
      type: string
      format: date-time
      paramType: query
    - name: queue
      description: queue name
      required: false
      type: string
      paramType: query
    - name: status
      description: job status
      required: false
      type: string
      enum:
        - queued
        - running
        - completed
      paramType: query
    - name: max_run_time
      description: maximum run time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_run_time
      description: minimum run time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_queue_time
      description: maximum queue time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_queue_time
      description: minimum queue time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_requested_time
      description: maximum requested time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_requested_time
      description: minimum requested time
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_nodes
      description: maximum nodes
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_nodes
      description: minimum nodes
      required: false
      type: integer
      format: int64
      paramType: query
    - name: max_cores
      description: maximum cores
      required: false
      type: integer
      format: int64
      paramType: query
    - name: min_cores
      description: minimum cores
      required: false
      type: integer
      format: int64
      paramType: query
    responseMessages:
        - code: 401
          message: Not authenticated
        - code: 403
          message: Insufficient rights to call this procedure
        - code: 500
          message: Internal Server Error
    """
    logger.debug('Characteristics plot requested by user: %s on %s.', request.user.username, resource_name)
    field = {}
    for param in request.query_params:
        val = request.query_params.get(param)
        field[param] = val
    order_key = '-id'
    if 'order_key' in field: 
        order_key = field['order_key']
        del field['order_key']
    logger.debug('Request params: %s', field)
    job_filter = JobFilter(request.GET, queryset=Job.objects.all())
    char_plot = machineViews.hist_summary(job_filter.qs, view_type='api')
    logger.debug('Plot generated for given queryset.')
    return Response({'status': 'success', 'message': '', 'result': char_plot})

@api_view(['GET'])
@authentication_classes((CustomTokenAuthentication,))
@permission_classes((IsAuthenticated,))
def device_data(request, pk, resource_name, device_name):
    """
    Returns device data for a job run on a resource.
    ---
    type:
      schema:
        required: true
        type: array
      device_name:
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
    - name: pk
      description: job id
      required: true
      type: integer
      format: int64
      paramType: path 
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
        - code: 401
          message: Not authenticated
        - code: 403
          message: Insufficient rights to call this procedure
        - code: 500
          message: Internal Server Error
    """
    logger.debug('Device data requested by user: %s, job id: %s, device name: %s, resource: %s', request.user.username, pk, device_name, resource_name)
    type_info = machineViews.type_info(resource_name, pk, device_name)
    logger.debug('Device data generated.')
    return Response({'status': 'success', 'message': '', 'result': type_info})
