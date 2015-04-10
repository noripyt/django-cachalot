# coding: utf-8

from __future__ import unicode_literals
import os


DATABASES = {
    'sqlite3': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'cachalot.sqlite3',
    },
    'postgresql': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'cachalot',
        'USER': 'cachalot',
        'HOST': 'localhost',
        'PORT': '5432',
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


CACHES = {
    'redis': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
        'OPTIONS': {
            # Since we are using both Python 2 & 3 in tests, we need to use
            # a compatible pickle version to avoid unpickling errors when
            # running a Python 2 test after a Python 3 test.
            'PICKLE_VERSION': 2,
        }
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
        }
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


MIGRATION_MODULES = {
    'cachalot': 'cachalot.tests.migrations'
}


MIDDLEWARE_CLASSES = ()
PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)
SECRET_KEY = 'it’s not important but we have to set it'


CACHALOT_ENABLED = True
