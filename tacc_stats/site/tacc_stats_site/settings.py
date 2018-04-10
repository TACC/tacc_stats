# Django settings for tacc_stats_site project.
import os
import tacc_stats.cfg as cfg
import tacc_stats.site.tacc_stats_site as tacc_stats_site
import tacc_stats.site.tacc_stats_site.settings_secret as settings_secret

DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG = True

ADMINS = (
    ('Richard Todd Evans', 'rtevans@tacc.utexas.edu'),
)

MANAGERS = ADMINS

# Give a name that is unique for the computing platform
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME'  : cfg.machine + '_db',
        'USER': 'taccstats',
        'PASSWORD': 'taccstats',
        'HOST': 'localhost',         
        'PORT': '5432',               
        },
    # Uncomment this portion if an xalt database exists
    'xalt' : {
        'ENGINE' : 'django.db.backends.mysql',
        'NAME' : 'xalt',
        'USER' : 'xaltUser',
        'PASSWORD' : 'kutwgbh',
        'HOST' : 'xalt'
        }        
    }

print '>>>>>>>>>>>>', DATABASES

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
MEDIA_ROOT = os.path.join(DIR,'media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(DIR,'static/'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'dcute6k4o*0%=76t6!2q=wqv4lt20v32(m!c_ueed^)x8q2u#8'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
        #    'tacc_stats_site/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'tacc_stats.site.tacc_stats_site.urls'
# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tacc_stats.site.tacc_stats_site.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'django_extensions',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    #'debug_toolbar',
    #'django_pdf',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'tacc_stats.site.machine',
    'tacc_stats.site.xalt',
    'tacc_stats.site.tacc_stats_site',
)
INTERNAL_IPS = ['127.0.0.1']
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = 'django.contrib.sessions.backends.file'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

CACHES = {
    'normal': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        },
    'default': {
        'BACKEND': 'tacc_stats.site.tacc_stats_site.cache.LargeMemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT' : None,
        },
}

#AGAVE_CLIENT_KEY= '5pGhxBUN3KjJDiufBi2Ar1ex1GEa'
#AGAVE_CLIENT_SECRET= 'wNu9vNHX6recy5Ak6PEFYrq7aJ4a'
#AGAVE_BASE_URL = 'https://api.tacc.utexas.edu/'

AGAVE_CLIENT_KEY = settings_secret._AGAVE_CLIENT_KEY
AGAVE_CLIENT_SECRET = settings_secret._AGAVE_CLIENT_SECRET
AGAVE_BASE_URL = settings_secret._AGAVE_BASE_URL