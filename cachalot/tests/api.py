# coding: utf-8

from __future__ import unicode_literals
try:
    from unittest import skipIf
except ImportError:  # For Python 2.6
    from unittest2 import skipIf

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.core.management import call_command
from django.db import connection, transaction, DEFAULT_DB_ALIAS
from django.test import TransactionTestCase

from ..api import *
from .models import Test


class APITestCase(TransactionTestCase):
    def setUp(self):
        self.t1 = Test.objects.create(name='test1')
        self.cursor = connection.cursor()
        self.is_sqlite = connection.vendor == 'sqlite'

    def test_invalidate_tables(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data1, ['test1'])

        with self.settings(CACHALOT_INVALIDATE_RAW=False):
            self.cursor.execute(
                "INSERT INTO cachalot_test (name, public) "
                "VALUES ('test2', %s);", [1 if self.is_sqlite else 'true'])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data2, ['test1'])

        invalidate_tables(['cachalot_test'])

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data3, ['test1', 'test2'])

    def test_invalidate_models(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data1, ['test1'])

        with self.settings(CACHALOT_INVALIDATE_RAW=False):
            self.cursor.execute(
                "INSERT INTO cachalot_test (name, public) "
                "VALUES ('test2', %s);", [1 if self.is_sqlite else 'true'])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data2, ['test1'])

        invalidate_models([Test])

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data3, ['test1', 'test2'])

    def test_invalidate_all(self):
        with self.assertNumQueries(1):
            Test.objects.get()

        with self.assertNumQueries(0):
            Test.objects.get()

        invalidate_all()

        with self.assertNumQueries(1):
            Test.objects.get()

    def test_invalidate_all_in_atomic(self):
        with transaction.atomic():
            with self.assertNumQueries(1):
                Test.objects.get()

            with self.assertNumQueries(0):
                Test.objects.get()

            invalidate_all()

            with self.assertNumQueries(1):
                Test.objects.get()

        with self.assertNumQueries(1):
            Test.objects.get()


class CommandTestCase(TransactionTestCase):
    multi_db = True

    def setUp(self):
        self.db_alias2 = next(alias for alias in settings.DATABASES
                              if alias != DEFAULT_DB_ALIAS)

        self.cache_alias2 = next(alias for alias in settings.CACHES
                                 if alias != DEFAULT_CACHE_ALIAS)

        self.t1 = Test.objects.create(name='test1')
        self.t2 = Test.objects.using(self.db_alias2).create(name='test2')
        self.u = User.objects.create_user('test')

    def test_invalidate_cachalot(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'auth', verbosity=0)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'cachalot', verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'cachalot.testchild', verbosity=0)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        call_command('invalidate_cachalot', 'cachalot.test', verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        with self.assertNumQueries(1):
            self.assertListEqual(list(User.objects.all()), [self.u])
        call_command('invalidate_cachalot', 'cachalot.test', 'auth.user',
                     verbosity=0)
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        with self.assertNumQueries(1):
            self.assertListEqual(list(User.objects.all()), [self.u])

    @skipIf(len(settings.DATABASES) == 1,
            'We can’t change the DB used since there’s only one configured')
    def test_invalidate_cachalot_multi_db(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0,
                     db_alias=self.db_alias2)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        with self.assertNumQueries(1, using=self.db_alias2):
            self.assertListEqual(list(Test.objects.using(self.db_alias2)),
                                 [self.t2])
        call_command('invalidate_cachalot', verbosity=0,
                     db_alias=self.db_alias2)
        with self.assertNumQueries(1, using=self.db_alias2):
            self.assertListEqual(list(Test.objects.using(self.db_alias2)),
                                 [self.t2])

    @skipIf(len(settings.CACHES) == 1,
            'We can’t change the cache used since there’s only one configured')
    def test_invalidate_cachalot_multi_cache(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0,
                     cache_alias=self.cache_alias2)
        with self.assertNumQueries(0):
            self.assertListEqual(list(Test.objects.all()), [self.t1])

        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                self.assertListEqual(list(Test.objects.all()), [self.t1])
        call_command('invalidate_cachalot', verbosity=0,
                     cache_alias=self.cache_alias2)
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                self.assertListEqual(list(Test.objects.all()), [self.t1])
