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

    def test_invalidate_tables(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data1, ['test1'])

        self.cursor.execute(
            "INSERT INTO cachalot_test (name, public) VALUES ('test2', 1);")

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
            "INSERT INTO cachalot_test (name, public) VALUES ('test2', true);")

        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data2, ['test1'])

        invalidate_models([Test])

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values_list('name', flat=True))
            self.assertListEqual(data3, ['test1', 'test2'])

    def clear(self):
        with self.assertNumQueries(1):
            Test.objects.get()

        with self.assertNumQueries(0):
            Test.objects.get()

        clear()

        with self.assertNumQueries(1):
            Test.objects.get()

    def clear_in_atomic(self):
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
