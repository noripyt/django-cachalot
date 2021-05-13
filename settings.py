import os

from django import VERSION as __DJ_V


DATABASES = {
    'sqlite3': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'cachalot.sqlite3',
    },
    'postgresql': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cachalot',
        'USER': 'cachalot',
        'HOST': '127.0.0.1',
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'cachalot',
        'USER': 'root',
        'HOST': '127.0.0.1',
    },
}
if 'MYSQL_PASSWORD' in os.environ:
    DATABASES['mysql']['PASSWORD'] = os.environ['MYSQL_PASSWORD']
if 'POSTGRES_PASSWORD' in os.environ:
    DATABASES['postgresql']['PASSWORD'] = os.environ['POSTGRES_PASSWORD']
for alias in DATABASES:
    if 'TEST' not in DATABASES[alias]:
        test_db_name = 'test_' + DATABASES[alias]['NAME']
        DATABASES[alias]['TEST'] = {'NAME': test_db_name}

DATABASES['default'] = DATABASES.pop(os.environ.get('DB_ENGINE', 'sqlite3'))
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
DATABASE_ROUTERS = ['cachalot.tests.db_router.PostgresRouter']

CACHES = {
    'redis': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
        'OPTIONS': {
            # Since we are using both Python 2 & 3 in tests, we need to use
            # a compatible pickle version to avoid unpickling errors when
            # running a Python 2 test after a Python 3 test.
            'PICKLE_VERSION': 2,
        },
    },
    'memcached': {
        'BACKEND': 'django.core.cache.backends.memcached.'
                   + ('PyMemcacheCache' if __DJ_V[0] > 2
                      and (__DJ_V[1] > 1 or __DJ_V[0] > 3) else 'MemcachedCache'),
        'LOCATION': '127.0.0.1:11211',
    },
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'OPTIONS': {
            # We want that limit to be infinite, otherwise we can’t
            # reliably count the number of SQL queries executed in tests.

            # In this context, 10e9 is enough to be considered
            # infinite.
            'MAX_ENTRIES': 10e9,
        }
    },
    'filebased': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10e9,  # (See locmem)
        },
    }
}

try:
    import pylibmc
except ImportError:
    pass
else:
    CACHES['pylibmc'] = {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
    }

DEFAULT_CACHE_ALIAS = os.environ.get('CACHE_BACKEND', 'locmem')
CACHES['default'] = CACHES.pop(DEFAULT_CACHE_ALIAS)
if DEFAULT_CACHE_ALIAS == 'memcached' and 'pylibmc' in CACHES:
    del CACHES['pylibmc']
elif DEFAULT_CACHE_ALIAS == 'pylibmc':
    del CACHES['memcached']

INSTALLED_APPS = [
    'cachalot',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.postgres',  # Enables the unaccent lookup.
]

MIGRATION_MODULES = {
    'cachalot': 'cachalot.tests.migrations',
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
    },
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            'extensions': [
                'cachalot.jinja2ext.cachalot',
            ],
        },
    }
]

MIDDLEWARE = []
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
SECRET_KEY = 'it’s not important in tests but we have to set it'

USE_TZ = False  # Time zones are not supported by MySQL, we only enable it in tests when needed.
TIME_ZONE = 'UTC'

CACHALOT_ENABLED = True

#
# Settings for django-debug-toolbar
#

# We put django-debug-toolbar before to reproduce the conditions of this issue:
# https://github.com/noripyt/django-cachalot/issues/62
INSTALLED_APPS = [
    'debug_toolbar',
] + INSTALLED_APPS + ['django.contrib.staticfiles']

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'cachalot.panels.CachalotPanel',
]

DEBUG_TOOLBAR_CONFIG = {
    # Django’s test client sets wsgi.multiprocess to True inappropriately.
    'RENDER_PANELS': False,
}

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = ['127.0.0.1']
ROOT_URLCONF = 'runtests_urls'
STATIC_URL = '/static/'
