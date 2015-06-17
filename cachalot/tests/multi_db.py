# coding: utf-8

from __future__ import unicode_literals
try:
    from unittest import skipIf
except ImportError:  # For Python 2.6
    from unittest2 import skipIf

from django import VERSION as django_version
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections
from django.test import TransactionTestCase

from .models import Test


@skipIf(len(settings.DATABASES) == 1,
        'We can’t change the DB used since there’s only one configured')
class MultiDatabaseTestCase(TransactionTestCase):
    multi_db = True

    def setUp(self):
        self.t1 = Test.objects.create(name='test1')
        self.t2 = Test.objects.create(name='test2')
        self.db_alias2 = next(alias for alias in settings.DATABASES
                              if alias != DEFAULT_DB_ALIAS)
        connection2 = connections[self.db_alias2]
        self.is_sqlite2 = connection2.vendor == 'sqlite'
        self.is_mysql2 = connection2.vendor == 'mysql'
        if django_version >= (1, 7) and self.is_mysql2:
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection2.cursor()

    def test_read(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
            self.assertListEqual(data1, [self.t1, self.t2])

        with self.assertNumQueries(1, using=self.db_alias2):
            data2 = list(Test.objects.using(self.db_alias2))
            self.assertListEqual(data2, [])

        with self.assertNumQueries(0, using=self.db_alias2):
            data3 = list(Test.objects.using(self.db_alias2))
            self.assertListEqual(data3, [])

    def test_invalidate_other_db(self):
        """
        Tests if the non-default database is invalidated when modified.
        """
        with self.assertNumQueries(1, using=self.db_alias2):
            data1 = list(Test.objects.using(self.db_alias2))
            self.assertListEqual(data1, [])

        with self.assertNumQueries(2 if self.is_sqlite2 else 1,
                                   using=self.db_alias2):
            t3 = Test.objects.using(self.db_alias2).create(name='test3')

        with self.assertNumQueries(1, using=self.db_alias2):
            data2 = list(Test.objects.using(self.db_alias2))
            self.assertListEqual(data2, [t3])

    def test_invalidation_independence(self):
        """
        Tests if invalidation doesn’t affect the unmodified databases.
        """
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
            self.assertListEqual(data1, [self.t1, self.t2])

        with self.assertNumQueries(2 if self.is_sqlite2 else 1,
                                   using=self.db_alias2):
            Test.objects.using(self.db_alias2).create(name='test3')

        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
            self.assertListEqual(data2, [self.t1, self.t2])
