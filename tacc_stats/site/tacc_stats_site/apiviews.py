from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from serializers import UserSerializer, GroupSerializer, JobSerializer,JobDetailSerializer
from stampede.models import Job
from lonestar.models import LS4Job
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

class UserViewSet(viewsets.ModelViewSet):
      """
      API endpoint that allows users to be viewed or edited.
      """
      queryset = User.objects.all()
      serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
      """
      API endpoint that allows groups to be viewed or edited.
      """
      queryset = Group.objects.all()
      serializer_class = GroupSerializer


class JobsView(object):
     def apply_filter(this,resource_job):
           request = this.request
           queryset = resource_job.objects.all()
           # check for any url query parameters and filter accordingly

           user = request.QUERY_PARAMS.get('user', None)
           project_id = request.QUERY_PARAMS.get('project_id', None)
           job_id = request.QUERY_PARAMS.get('job_id', None)
           #start_time = request.QUERY_PARAMS.get('start_time', None)
           #end_time = request.QUERY_PARAMS.get('end_time', None)
           #run_time = request.QUERY_PARAMS.get('run_time', None)
           #queue_time = request.QUERY_PARAMS.get('queue_time', None)
           queue = request.QUERY_PARAMS.get('queue', None)
           status = request.QUERY_PARAMS.get('status', None)
           if user is not None:
                queryset = queryset.filter(user=user)
           if project_id is not None:
                queryset = queryset.filter(project=project_id)
           if job_id is not None:
                queryset = queryset.filter(id=job_id)
           if queue is not None:
                queryset = queryset.filter(queue=queue)
           if status is not None:
                queryset = queryset.filter(status=status)
           return queryset

class StampedeJobsViewSet(viewsets.ReadOnlyModelViewSet,JobsView):
    """
    Jobs can be filtered using url query parameters mentioned below (FOR LIST RESPONSE ONLY).
    user -- name of the user
    project_id -- id of the project that ran this job
    job_id -- id of the job
    queue -- name of the queue
    status -- status of the job
    """
    serializer_class = JobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    #paginate_by = 100
    def list(self,request):
        """
        Returns jobs run on Stampede.
        """
        print 'stampede list ----------------------------------------------------------------------------'
        queryset = JobsView.apply_filter(self,Job)
        serializer = JobSerializer(queryset,many=True)
        print 'stampede list2 ----------------------------------------------------------------------------'
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Returns a job run on Stampede by job id.
        """
        queryset = Job.objects.all()
        job = get_object_or_404(queryset, pk=pk)
        serializer = JobDetailSerializer(job)
        return Response(serializer.data)
     
class LonestarJobsViewSet(viewsets.ReadOnlyModelViewSet,JobsView):
    """
    Jobs can be filtered using url query parameters mentioned below (FOR LIST RESPONSE ONLY).
    user -- name of the user
    project_id -- id of the project that ran this job
    job_id -- id of the job
    queue -- name of the queue
    status -- status of the job
    """
    serializer_class = JobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    #paginate_by = 100
    def list(self,request):
        """
        Returns jobs run on Lonestar.
        """
        print 'lonestar list ----------------------------------------------------------------------------'
        queryset = JobsView.apply_filter(self,LS4Job)
        serializer = JobSerializer(queryset,many=True)
        print 'lonestar2 list ----------------------------------------------------------------------------'
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Returns a job run on Lonestar by job id.
        """
        queryset = LS4Job.objects.all()
        job = get_object_or_404(queryset, pk=pk)
        serializer = JobDetailSerializer(job)
        return Response(serializer.data)
