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
   API endpoint that returns jobs run by a user
   """
   queryset = Job.objects.all()
   serializer_class = JobSerializer

class UserJobsViewSet(viewsets.ModelViewSet):
      """
      API endpoint that returns jobs run by a user
      """
      serializer_class = JobSerializer
      permission_classes = (IsAuthenticatedOrReadOnly,)
      def get_queryset(self):
          # user = self.kwargs['user']
           queryset = Job.objects.all()
           user = self.request.QUERY_PARAMS.get('user', None)
           if user is not None:
                queryset = queryset.filter(user=user)
           return queryset
     
#@csrf_exempt
#def UserJobs(request, user):
#     """
#     Comment
#     """  
#     jobs = Job.objects.filter(user=user)
#     serializer = JobSerializer(jobs,many=True)
#     return JSONResponse(serializer.data)

