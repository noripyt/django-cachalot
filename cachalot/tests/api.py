# coding: utf-8

from __future__ import unicode_literals

from django.db import connection, transaction
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

        self.cursor.execute(
            "INSERT INTO cachalot_test (name, public) VALUES ('test2', %s);",
            [1 if self.is_sqlite else 'true'])

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

        self.cursor.execute(
            "INSERT INTO cachalot_test (name, public) VALUES ('test2', %s);",
            [1 if self.is_sqlite else 'true'])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data2, ['test1'])

        invalidate_models([Test])

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data3, ['test1', 'test2'])

    def test_clear(self):
        with self.assertNumQueries(1):
            Test.objects.get()

        with self.assertNumQueries(0):
            Test.objects.get()

        clear()

        with self.assertNumQueries(1):
            Test.objects.get()

    def test_clear_in_atomic(self):
        with transaction.atomic():
            with self.assertNumQueries(1):
                Test.objects.get()

            with self.assertNumQueries(0):
                Test.objects.get()

            clear()

            with self.assertNumQueries(1):
                Test.objects.get()

        with self.assertNumQueries(0):
            Test.objects.get()
