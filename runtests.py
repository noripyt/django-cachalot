#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals
import sys
from django.conf import settings

settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        },
    },
    INSTALLED_APPS=(
        'cachalot',
        'django.contrib.auth',
        'django.contrib.contenttypes',
    ),
)


if __name__ == '__main__':
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner()
    failures = test_runner.run_tests(['cachalot'])
    if failures:
        sys.exit(failures)
