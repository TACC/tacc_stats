from django.contrib.auth.models import User, Group, Permission
from rest_framework import viewsets, generics
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from serializers import UserSerializer, GroupSerializer, JobSerializer
from stampede.models import Job
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

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


class JobsViewSet(viewsets.ModelViewSet):
      """
      API endpoint that returns all jobs or run by a user
      """
      serializer_class = JobSerializer
      permission_classes = (IsAuthenticatedOrReadOnly,)
      def get_queryset(self):
           queryset = Job.objects.all()
           # check for any url query parameters and filter accordingly

           user = self.request.QUERY_PARAMS.get('user', None)
           job_id = self.request.QUERY_PARAMS.get('job_id', None)
           project_id = self.request.QUERY_PARAMS.get('project_id', None)
           uid = self.request.QUERY_PARAMS.get('uid', None)
           start_time = self.request.QUERY_PARAMS.get('start_time', None)
           end_time = self.request.QUERY_PARAMS.get('end_time', None)
           run_time = self.request.QUERY_PARAMS.get('run_time', None)
           queue_time = self.request.QUERY_PARAMS.get('queue_time', None)
           queue = self.request.QUERY_PARAMS.get('queue', None)
           status = self.request.QUERY_PARAMS.get('status', None)
           if user is not None:
                queryset = queryset.filter(user=user)
           if job_id is not None:
                queryset = queryset.filter(id=job_id)
           if project_id is not None:
                queryset = queryset.filter(project=project_id)
           if uid is not None:
                queryset = queryset.filter(uid=uid) 
           if queue is not None:
                queryset = queryset.filter(queue=queue)
           if status is not None:
                queryset = queryset.filter(status=status)
           return queryset
     
#@csrf_exempt
#def UserJobs(request, user):
#     """
#     Comment
#     """  
#     jobs = Job.objects.filter(user=user)
#     serializer = JobSerializer(jobs,many=True)
#     return JSONResponse(serializer.data)

