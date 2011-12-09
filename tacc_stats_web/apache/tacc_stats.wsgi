import os, sys

#Calculate the path based on the location of the WSGI script.
apache_configuration= os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.dirname(project)
sys.path.append(workspace)
print >> sys.stderr, apache_configuration
print >> sys.stderr, project
print >> sys.stderr, workspace

#sys.path.append('/var/www')
#sys.path.append('/var/www/django_sites')

print >> sys.stderr, sys.path


#Add the path to 3rd party django application and to django itself.
#sys.path.append('C:\\yml\\_myScript_\\dj_things\\web_development\\svn_views\\django-registration')

os.environ['DJANGO_SETTINGS_MODULE'] = 'tacc_stats_web.settings'#'dj_project.apache.settings_production'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
