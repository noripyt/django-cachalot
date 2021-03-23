from unittest import skipIf

from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from django.test import TransactionTestCase

from .models import Test


@skipIf(len(settings.DATABASES) == 1,
        'We can’t change the DB used since there’s only one configured')
class MultiDatabaseTestCase(TransactionTestCase):
    multi_db = True
    databases = "__all__"

    def setUp(self):
        self.t1 = Test.objects.create(name='test1')
        self.t2 = Test.objects.create(name='test2')
        self.db_alias2 = next(alias for alias in settings.DATABASES
                              if alias != DEFAULT_DB_ALIAS)
        connection2 = connections[self.db_alias2]
        self.is_sqlite2 = connection2.vendor == 'sqlite'
        self.is_mysql2 = connection2.vendor == 'mysql'
        if connection2.vendor in ('mysql', 'postgresql'):
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection2.cursor()

    def is_django_21_below_and_sqlite2(self):
        """
        Note: See test_utils.py with this function name
        Checks if Django 2.1 or below and SQLite2
        """
        django_version = DJANGO_VERSION
        if not self.is_sqlite2:
            # Immediately know if SQLite
            return False
        if django_version[0] < 2:
            # Takes Django 0 and 1 out of the picture
            return True
        else:
            if django_version[0] == 2 and django_version[1] < 2:
                # Takes Django 2.0-2.1 out
                return True
            return False

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

        with self.assertNumQueries(2 if self.is_django_21_below_and_sqlite2() else 1,
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

        with self.assertNumQueries(2 if self.is_django_21_below_and_sqlite2() else 1,
                                   using=self.db_alias2):
            Test.objects.using(self.db_alias2).create(name='test3')

        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
            self.assertListEqual(data2, [self.t1, self.t2])

    def test_heterogeneous_atomics(self):
        """
        Checks that an atomic block for a database nested inside
        another atomic block for another database has no impact on their
        caching.
        """
        with transaction.atomic():
            with transaction.atomic(self.db_alias2):
                with self.assertNumQueries(1):
                    data1 = list(Test.objects.all())
                    self.assertListEqual(data1, [self.t1, self.t2])
                with self.assertNumQueries(1, using=self.db_alias2):
                    data2 = list(Test.objects.using(self.db_alias2))
                    self.assertListEqual(data2, [])
                t3 = Test.objects.using(self.db_alias2).create(name='test3')
                with self.assertNumQueries(1, using=self.db_alias2):
                    data3 = list(Test.objects.using(self.db_alias2))
                    self.assertListEqual(data3, [t3])

            with self.assertNumQueries(0):
                data4 = list(Test.objects.all())
                self.assertListEqual(data4, [self.t1, self.t2])

            with self.assertNumQueries(1):
                data5 = list(Test.objects.filter(name='test3'))
                self.assertListEqual(data5, [])

    def test_heterogeneous_atomics_independence(self):
        """
        Checks that interrupting an atomic block after the commit of another
        atomic block for another database nested inside it
        correctly invalidates the cache for the committed transaction.
        """
        with self.assertNumQueries(1, using=self.db_alias2):
            data1 = list(Test.objects.using(self.db_alias2))
            self.assertListEqual(data1, [])

        try:
            with transaction.atomic():
                with transaction.atomic(self.db_alias2):
                    t3 = Test.objects.using(
                        self.db_alias2).create(name='test3')
                raise ZeroDivisionError
        except ZeroDivisionError:
            pass
        with self.assertNumQueries(1, using=self.db_alias2):
            data2 = list(Test.objects.using(self.db_alias2))
            self.assertListEqual(data2, [t3])
