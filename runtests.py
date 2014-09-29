#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals
import os
import sys

import django
from django.conf import settings
from django.test.runner import DiscoverRunner


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
}


CACHES = {
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'redis': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:0',
    }
}

settings.configure(
    DEBUG=True,
    DATABASES={'default': DATABASES[os.environ.get('DB_BACKEND', 'sqlite3')]},
    INSTALLED_APPS=(
        'cachalot',
        'django.contrib.auth',
        'django.contrib.contenttypes',
    ),
    CACHES={'default': CACHES[os.environ.get('CACHE_BACKEND', 'locmem')]},
    MIDDLEWARE_CLASSES=(),
)


if __name__ == '__main__':
    if django.VERSION[:2] >= (1, 7):
        django.setup()

    test_runner = DiscoverRunner()
    failures = test_runner.run_tests(['cachalot'])
    if failures:
        sys.exit(failures)
