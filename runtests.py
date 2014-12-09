#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals
import os
import sys
import django


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    if django.VERSION[:2] >= (1, 7):
        django.setup()
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=2)
    failures = test_runner.run_tests(['cachalot.tests'])
    if failures:
        sys.exit(failures)
