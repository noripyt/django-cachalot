# coding: utf-8

from __future__ import unicode_literals
try:
    from unittest import skipIf
except ImportError:  # For Python 2.6
    from unittest2 import skipIf

from django import VERSION as django_version
from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import override_settings

from .models import Test


class SettingsTestCase(TransactionTestCase):
    def setUp(self):
        if django_version >= (1, 7) and connection.vendor == 'mysql':
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

    @override_settings(CACHALOT_ENABLED=False)
    def test_decorator(self):
        with self.assertNumQueries(1):
            list(Test.objects.all())
        with self.assertNumQueries(1):
            list(Test.objects.all())

    def test_django_override(self):
        with self.settings(CACHALOT_ENABLED=False):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.settings(CACHALOT_ENABLED=True):
                with self.assertNumQueries(1):
                    list(Test.objects.all())
                with self.assertNumQueries(0):
                    list(Test.objects.all())

    def test_enabled(self):
        with self.settings(CACHALOT_ENABLED=True):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(0):
                list(Test.objects.all())

        with self.settings(CACHALOT_ENABLED=False):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(1):
                list(Test.objects.all())

        with self.assertNumQueries(0):
            list(Test.objects.all())

        is_sqlite = connection.vendor == 'sqlite'

        with self.settings(CACHALOT_ENABLED=False):
            with self.assertNumQueries(2 if is_sqlite else 1):
                t = Test.objects.create(name='test')
        with self.assertNumQueries(1):
            data = list(Test.objects.all())
        self.assertListEqual(data, [t])

    @skipIf(len(settings.CACHES) == 1,
            'We can’t change the cache used since there’s only one configured')
    def test_cache(self):
        with self.settings(CACHALOT_CACHE=DEFAULT_CACHE_ALIAS):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(0):
                list(Test.objects.all())

        other_cache_alias = next(alias for alias in settings.CACHES
                                 if alias != DEFAULT_CACHE_ALIAS)

        with self.settings(CACHALOT_CACHE=other_cache_alias):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(0):
                list(Test.objects.all())

    def test_cache_random(self):
        with self.assertNumQueries(1):
            list(Test.objects.order_by('?'))
        with self.assertNumQueries(1):
            list(Test.objects.order_by('?'))

        with self.settings(CACHALOT_CACHE_RANDOM=True):
            with self.assertNumQueries(1):
                list(Test.objects.order_by('?'))
            with self.assertNumQueries(0):
                list(Test.objects.order_by('?'))

    def test_invalidate_raw(self):
        with self.assertNumQueries(1):
            list(Test.objects.all())
        with self.settings(CACHALOT_INVALIDATE_RAW=False):
            with self.assertNumQueries(1):
                cursor = connection.cursor()
                cursor.execute("UPDATE %s SET name = 'new name';"
                               % Test._meta.db_table)
                cursor.close()
        with self.assertNumQueries(0):
            list(Test.objects.all())

    def test_uncachable_tables(self):
        with self.settings(CACHALOT_UNCACHABLE_TABLES=('cachalot_test',)):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(1):
                list(Test.objects.all())

        with self.assertNumQueries(1):
            list(Test.objects.all())
        with self.assertNumQueries(0):
            list(Test.objects.all())

        with self.settings(CACHALOT_UNCACHABLE_TABLES=('cachalot_test',)):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(1):
                list(Test.objects.all())
