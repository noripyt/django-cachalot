# coding: utf-8

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import connection, transaction
from django.test import TransactionTestCase

from .models import Test


class AtomicTestCase(TransactionTestCase):
    def setUp(self):
        if connection.vendor == 'mysql':
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

    def test_successful_read_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            with transaction.atomic():
                data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [])

    def test_unsuccessful_read_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            try:
                with transaction.atomic():
                    data1 = list(Test.objects.all())
                    raise ZeroDivisionError
            except ZeroDivisionError:
                pass
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [])

    def test_successful_write_atomic(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            with transaction.atomic():
                t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [t1])

        with self.assertNumQueries(2 if is_sqlite else 1):
            with transaction.atomic():
                t2 = Test.objects.create(name='test2')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1, t2])

        with self.assertNumQueries(4 if is_sqlite else 3):
            with transaction.atomic():
                data4 = list(Test.objects.all())
                t3 = Test.objects.create(name='test3')
                t4 = Test.objects.create(name='test4')
                data5 = list(Test.objects.all())
        self.assertListEqual(data4, [t1, t2])
        self.assertListEqual(data5, [t1, t2, t3, t4])
        self.assertNotEqual(t4, t3)

    def test_unsuccessful_write_atomic(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            try:
                with transaction.atomic():
                    Test.objects.create(name='test')
                    raise ZeroDivisionError
            except ZeroDivisionError:
                pass
        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [])
        with self.assertNumQueries(1):
            with self.assertRaises(Test.DoesNotExist):
                Test.objects.get(name='test')

    def test_cache_inside_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            with transaction.atomic():
                data1 = list(Test.objects.all())
                data2 = list(Test.objects.all())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [])

    def test_invalidation_inside_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(4 if is_sqlite else 3):
            with transaction.atomic():
                data1 = list(Test.objects.all())
                t = Test.objects.create(name='test')
                data2 = list(Test.objects.all())
        self.assertListEqual(data1, [])
        self.assertListEqual(data2, [t])

    def test_successful_nested_read_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(7 if is_sqlite else 6):
            with transaction.atomic():
                list(Test.objects.all())
                with transaction.atomic():
                    list(User.objects.all())
                    with self.assertNumQueries(2):
                        with transaction.atomic():
                            list(User.objects.all())
                with self.assertNumQueries(0):
                    list(User.objects.all())
        with self.assertNumQueries(0):
            list(Test.objects.all())
            list(User.objects.all())

    def test_unsuccessful_nested_read_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'
        num_queries = 6 if is_sqlite else 5

        with self.assertNumQueries(num_queries):
            with transaction.atomic():
                try:
                    with transaction.atomic():
                        with self.assertNumQueries(1):
                            list(Test.objects.all())
                        raise ZeroDivisionError
                except ZeroDivisionError:
                    pass
                with self.assertNumQueries(1):
                    list(Test.objects.all())

    def test_successful_nested_write_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(13 if is_sqlite else 12):
            with transaction.atomic():
                t1 = Test.objects.create(name='test1')
                with transaction.atomic():
                    t2 = Test.objects.create(name='test2')
                data1 = list(Test.objects.all())
                self.assertListEqual(data1, [t1, t2])
                with transaction.atomic():
                    t3 = Test.objects.create(name='test3')
                    with transaction.atomic():
                        data2 = list(Test.objects.all())
                        self.assertListEqual(data2, [t1, t2, t3])
                        t4 = Test.objects.create(name='test4')
        data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1, t2, t3, t4])

    def test_unsuccessful_nested_write_atomic(self):
        is_sqlite = connection.vendor == 'sqlite'
        num_queries = 16 if is_sqlite else 15

        with self.assertNumQueries(num_queries):
            with transaction.atomic():
                t1 = Test.objects.create(name='test1')
                try:
                    with transaction.atomic():
                        t2 = Test.objects.create(name='test2')
                        data1 = list(Test.objects.all())
                        self.assertListEqual(data1, [t1, t2])
                        raise ZeroDivisionError
                except ZeroDivisionError:
                    pass
                data2 = list(Test.objects.all())
                self.assertListEqual(data2, [t1])
                try:
                    with transaction.atomic():
                        t3 = Test.objects.create(name='test3')
                        with transaction.atomic():
                            data2 = list(Test.objects.all())
                            self.assertListEqual(data2, [t1, t3])
                            raise ZeroDivisionError
                except ZeroDivisionError:
                    pass
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1])
