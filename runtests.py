#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals
import os
import sys


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner()
    failures = test_runner.run_tests(['cachalot.tests'])
    if failures:
        sys.exit(failures)
