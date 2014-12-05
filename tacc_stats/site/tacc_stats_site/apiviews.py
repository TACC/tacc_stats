from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework_extensions.mixins import PaginateByMaxMixin
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from serializers import UserSerializer, StampedeJobSerializer, StampedeJobDetailSerializer, LonestarJobSerializer,LonestarJobDetailSerializer
from stampede.models import Job
from stampede import stampedeapiviews
from lonestar.models import LS4Job
from lonestar import lonestarapiviews
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import detail_route
from rest_framework import status
from renderers import TACCJSONRenderer

def permission_denied_handler(request):
    from django.http import HttpResponse
    return HttpResponse("You do not have required permissions!")

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

class JobsView(object):
     def apply_filter(this,resource_job):
           request = this.request
           queryset = resource_job.objects.all()
           # check for any url query parameters and filter accordingly

           user = request.QUERY_PARAMS.get('user', None)
           project_id = request.QUERY_PARAMS.get('project_id', None)
           job_id = request.QUERY_PARAMS.get('job_id', None)
           start_time = request.QUERY_PARAMS.get('start_time', None)
           end_time = request.QUERY_PARAMS.get('end_time', None)
           queue = request.QUERY_PARAMS.get('queue', None)
           status = request.QUERY_PARAMS.get('status', None)

           if user is not None:
                queryset = queryset.filter(user=user)
           if project_id is not None:
                queryset = queryset.filter(project=project_id)
           if job_id is not None:
                queryset = queryset.filter(id=job_id)
           if start_time is not None:
                queryset = queryset.filter(start_time__gte=start_time)
           if end_time is not None:
                queryset = queryset.filter(end_time__gte=end_time)
           if queue is not None:
                queryset = queryset.filter(queue__iexact=queue)
           if status is not None:
                queryset = queryset.filter(status__iexact=status)
           return queryset

class StampedeJobsViewSet(viewsets.ReadOnlyModelViewSet, JobsView):
    serializer_class = StampedeJobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    renderer_classes = (TACCJSONRenderer,)
    def list(self,request):
        """
        Returns jobs run on Stampede.
        ---
        # YAML (must be separated by `---`)

        serializer: LonestarJobSerializer
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
        queryset = JobsView.apply_filter(self,Job)
        serializer = StampedeJobSerializer(queryset,many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Returns a job run on Stampede by job id.
        ---
        # YAML (must be separated by `---`)

        serializer: StampedeJobDetailSerializer
        omit_serializer: false
        parameters_strategy: replace
        responseMessages:
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """
        queryset = Job.objects.all()
        job = get_object_or_404(queryset, pk=pk)
        serializer = StampedeJobDetailSerializer(job)
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
        type_name = request.QUERY_PARAMS.get('type', None)
        type_info = stampedeapiviews.type_info(pk,type_name)
        return Response(type_info)

class LonestarJobsViewSet(viewsets.ReadOnlyModelViewSet,JobsView):
    serializer_class = LonestarJobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    renderer_classes = (TACCJSONRenderer,)
    def list(self,request):
        """
        Returns jobs run on Lonestar.
        ---
        # YAML (must be separated by `---`)

        serializer: LonestarJobSerializer
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
        queryset = JobsView.apply_filter(self,LS4Job)
        serializer = LonestarJobSerializer(queryset,many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Returns a job run on Lonestar by job id.
        ---
        # YAML (must be separated by `---`)

        serializer: LonestarJobDetailSerializer
        omit_serializer: false
        parameters_strategy: replace
        responseMessages:
            - code: 500
              message: Internal Server Error
            - code: 405
              message: Method Not Allowed Error
        """
        queryset = LS4Job.objects.all()
        job = get_object_or_404(queryset, pk=pk)
        serializer = LonestarJobDetailSerializer(job)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def type_info(self, request, pk=None):
        """
        Returns type info for a job run on Lonestar.
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
        type_name = request.QUERY_PARAMS.get('type', None)
        type_info = lonestarapiviews.type_info(pk,type_name)
        return Response(type_info)
