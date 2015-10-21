# Django settings for site.
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'NOT_A_SECRET')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = False

ADMINS = (
    ('Richard Todd Evans', 'rtevans@tacc.utexas.edu'),
    ('Ajit Gauli', 'agauli@tacc.utexas.edu'),
)

MANAGERS = ADMINS

SOUTH_TESTS_MIGRATE = False

# Give a name that is unique for the computing platform
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'tacc_stats_db'
    }     
    }

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = '/var/www/statsapi/static/'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tacc_stats_site.middleware.ProfileMiddleware',

)

ROOT_URLCONF = 'tacc_stats_site.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tacc_stats.site.tacc_stats_site.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR,'tacc_stats_site','templates'),
)


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'tacc_stats.site.machine',
    'tacc_stats.site.xalt',
    'tacc_stats_api',
    'rest_framework',
    'rest_framework_swagger',
    'django_filters'
)
"""
TEMPLATE_CONTEXT_PROCESSORS=(
        "django.core.context_processors.auth",
        "django.core.context_processors.debug",
        "django.core.context_processors.i18n",
        "django.core.context_processors.media",
        "django.core.context_processors.request",
        "django_pdf.context_processors.check_format", #<-- this line
    )
"""
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = 'django.contrib.sessions.backends.file'

AUTHENTICATION_BACKENDS = (
    'tacc_stats_api.auth.TASBackend',
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )

}

ANONYMOUS_USER_ID = -1

SWAGGER_SETTINGS = {
    "exclude_namespaces": [], # List URL namespaces to ignore
    "api_version": '0.1',  # Specify your API's version
    "api_path": "/",  # Specify the path to your API not a root level
    "enabled_methods": [  # Specify which methods to enable in Swagger UI
        'get',
        'post',
        'put',
        'patch',
        'delete'
    ],
    "api_key": '', #An API key
    "is_authenticated": False,  # Set to True to enforce user authentication,
    "is_superuser": False,  # Set to True to enforce admin only access
    "permission_denied_handler": None,
    "info": {
        'contact': 'agauli@tacc.utexas.edu',
        'description': '',
    },
    "permission_denied_handler": "tacc_stats_api.views.permission_denied_handler",
    'title': 'TACC Stats API',
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(asctime)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'console': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
        'default': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'auth': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}

#default cache is 43200 seconds = 12 hrs
CACHES = {
    'normal': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'memcached:11211',
        },

    'default': { 
        'BACKEND':'tacc_stats.site.tacc_stats_site.cache.LargeMemcachedCache',
        'LOCATION': 'memcached:11211',
        'TIMEOUT': 43200,
        }
    }

