#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals
import sys

from settings import configure


if __name__ == '__main__':
    configure()
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner()
    failures = test_runner.run_tests(['cachalot.tests'])
    if failures:
        sys.exit(failures)
