#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals
import os
import sys

import django
from django.conf import settings


DATABASES = {
    'sqlite3': {
        'ENGINE': 'django.db.backends.sqlite3',
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
DEFAULT_DATABASE_KEY = os.environ.get('DB_ENGINE', 'sqlite3')
DATABASES['default'] = DATABASES[DEFAULT_DATABASE_KEY]
del DATABASES[DEFAULT_DATABASE_KEY]

CACHES = {
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'redis': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:0',
    },
    'memcached': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    },
}
DEFAULT_CACHE_KEY = os.environ.get('CACHE_BACKEND', 'locmem')
CACHES['default'] = CACHES[DEFAULT_CACHE_KEY]
del CACHES[DEFAULT_CACHE_KEY]

INSTALLED_APPS = [
    'cachalot',
    'django.contrib.auth',
    'django.contrib.contenttypes',
]
if django.VERSION < (1, 7):
    INSTALLED_APPS.append('south')

settings.configure(
    INSTALLED_APPS=INSTALLED_APPS,
    DATABASES=DATABASES,
    CACHES=CACHES,
    MIDDLEWARE_CLASSES=(),
    PASSWORD_HASHERS=('django.contrib.auth.hashers.MD5PasswordHasher',),
)

if django.VERSION[:2] >= (1, 7):
    django.setup()


if __name__ == '__main__':
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner()
    failures = test_runner.run_tests(['cachalot.tests'])
    if failures:
        sys.exit(failures)
