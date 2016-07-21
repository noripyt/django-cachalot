# coding: utf-8

from __future__ import unicode_literals
import os

from django import VERSION as django_version


if django_version[:2] >= (1, 9):
    POSTGRES_ENGINE = 'django.db.backends.postgresql'
else:
    POSTGRES_ENGINE = 'django.db.backends.postgresql_psycopg2'

DATABASES = {
    'sqlite3': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'cachalot.sqlite3',
    },
    'postgresql': {
        'ENGINE': POSTGRES_ENGINE,
        'NAME': 'cachalot',
        'USER': 'cachalot',
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'cachalot',
        'USER': 'root',
    },
}
for alias in DATABASES:
    test_db_name = 'test_' + DATABASES[alias]['NAME']
    DATABASES[alias]['TEST'] = {'NAME': test_db_name}

DATABASES['default'] = DATABASES.pop(os.environ.get('DB_ENGINE', 'sqlite3'))


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
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
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
]

if django_version[:2] >= (1, 8):
    INSTALLED_APPS.append(
        'django.contrib.postgres',  # Enables the unaccent lookup.
    )


MIGRATION_MODULES = {
    'cachalot': 'cachalot.tests.migrations',
}


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
    },
]


MIDDLEWARE_CLASSES = ()
PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)
SECRET_KEY = 'it’s not important but we have to set it'


USE_TZ = False  # Time zones are not supported by MySQL,
                # we only enable it in tests when needed.
TIME_ZONE = 'UTC'


CACHALOT_ENABLED = True
