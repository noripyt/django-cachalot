# coding: utf-8

from __future__ import unicode_literals
from unittest import skipUnless

from django import VERSION as django_version
from django.db import connection
from django.test import TransactionTestCase
from psycopg2._range import NumericRange

from .models import PostgresModel


@skipUnless(connection.vendor == 'postgresql' and django_version[:2] >= (1, 8),
            'This test is only for PostgreSQL and Django >= 1.8')
class PostgresReadTest(TransactionTestCase):
    def setUp(self):
        self.obj = PostgresModel.objects.create(
            int_array=[1, 2, 3], int_range=[1900, 2000])

    def test_int_array(self):
        with self.assertNumQueries(1):
            data1 = [o.int_array for o in PostgresModel.objects.all()]
        with self.assertNumQueries(0):
            data2 = [o.int_array for o in PostgresModel.objects.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [[1, 2, 3]])

    def test_int_range(self):
        with self.assertNumQueries(1):
            data1 = [o.int_range for o in PostgresModel.objects.all()]
        with self.assertNumQueries(0):
            data2 = [o.int_range for o in PostgresModel.objects.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [NumericRange(1900, 2000)])
