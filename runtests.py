#!/usr/bin/env python
import os
import sys
import django


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    django.setup()
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=2, interactive=False)
    failures = test_runner.run_tests(['cachalot.tests'])
    if failures:
        sys.exit(failures)
