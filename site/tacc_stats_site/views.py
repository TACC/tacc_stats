from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
import settings

def home(request):

    return render_to_response("tacc_stats_site/home.html",{"MEDIA_URL" : settings.MEDIA_URL})
