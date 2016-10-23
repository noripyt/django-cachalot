# coding: utf-8

from __future__ import unicode_literals
from datetime import date, datetime
from decimal import Decimal
from platform import python_version_tuple
from unittest import skipUnless, skipIf

from django import VERSION as django_version
from django.core.cache import caches
from django.core.cache.backends.filebased import FileBasedCache
from django.db import connection
from django.test import TransactionTestCase, override_settings
from psycopg2.extras import NumericRange, DateRange, DateTimeTZRange
from pytz import timezone

from .models import PostgresModel, Test

DJANGO_GTE_1_9 = django_version[:2] >= (1, 9)
if DJANGO_GTE_1_9:
    from django.contrib.postgres.functions import TransactionNow


# FIXME: Add tests for aggregations.


@skipUnless(connection.vendor == 'postgresql',
            'This test is only for PostgreSQL')
@skipIf(isinstance(caches['default'], FileBasedCache)
        and python_version_tuple()[:2] == ('2', '7'),
        'Caching psycopg2 objects is not working with file-based cache '
        'and Python 2.7 (see https://code.djangoproject.com/ticket/25501).')
@override_settings(USE_TZ=True)
class PostgresReadTestCase(TransactionTestCase):
    def setUp(self):
        self.obj1 = PostgresModel(
            int_array=[1, 2, 3],
            hstore={'a': 'b', 'c': None},
            int_range=[1900, 2000], float_range=[-1e3, 9.87654321],
            date_range=['1678-03-04', '1741-07-28'],
            datetime_range=[datetime(1989, 1, 30, 12, 20,
                                     tzinfo=timezone('Europe/Paris')), None])
        if DJANGO_GTE_1_9:
            self.obj1.json = {'a': 1, 'b': 2}
        self.obj1.save()

        self.obj2 = PostgresModel(
            int_array=[4, None, 6],
            hstore={'a': '1', 'b': '2'},
            int_range=[1989, None], float_range=[0.0, None],
            date_range=['1989-01-30', None],
            datetime_range=[None, None])
        if DJANGO_GTE_1_9:
            self.obj2.json = [
                'something',
                {
                    'a': 1,
                    'b': None,
                    'c': 123.456,
                    'd': True,
                    'e': {
                        'another': 'dict',
                        'and yet': {
                            'another': 'one',
                            'with a list': [],
                        },
                    },
                },
            ]
        self.obj2.save()

    def test_unaccent(self):
        Test.objects.create(name='Clémentine')
        Test.objects.create(name='Clementine')
        qs = Test.objects.filter(name__unaccent='Clémentine')
        with self.assertNumQueries(1):
            data1 = [t.name for t in qs.all()]
        with self.assertNumQueries(0):
            data2 = [t.name for t in qs.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, ['Clementine', 'Clémentine'])

    def test_int_array(self):
        qs = PostgresModel.objects.all()
        with self.assertNumQueries(1):
            data1 = [o.int_array for o in qs.all()]
        with self.assertNumQueries(0):
            data2 = [o.int_array for o in qs.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [[1, 2, 3], [4, None, 6]])

        qs = PostgresModel.objects.filter(int_array__contains=[3])
        with self.assertNumQueries(1):
            data3 = [o.int_array for o in qs.all()]
        with self.assertNumQueries(0):
            data4 = [o.int_array for o in qs.all()]
        self.assertListEqual(data4, data3)
        self.assertListEqual(data4, [[1, 2, 3]])

        qs = PostgresModel.objects.filter(int_array__contained_by=[1, 2, 3,
                                                                   4, 5, 6])
        with self.assertNumQueries(1):
            data7 = [o.int_array for o in qs.all()]
        with self.assertNumQueries(0):
            data8 = [o.int_array for o in qs.all()]
        self.assertListEqual(data8, data7)
        self.assertListEqual(data8, [[1, 2, 3]])

        qs = PostgresModel.objects.filter(int_array__overlap=[3, 4])
        with self.assertNumQueries(1):
            data9 = [o.int_array for o in qs.all()]
        with self.assertNumQueries(0):
            data10 = [o.int_array for o in qs.all()]
        self.assertListEqual(data10, data9)
        self.assertListEqual(data10, [[1, 2, 3], [4, None, 6]])

        qs = PostgresModel.objects.filter(int_array__len__in=(2, 3))
        with self.assertNumQueries(1):
            data11 = [o.int_array for o in qs.all()]
        with self.assertNumQueries(0):
            data12 = [o.int_array for o in qs.all()]
        self.assertListEqual(data12, data11)
        self.assertListEqual(data12, [[1, 2, 3], [4, None, 6]])

        qs = PostgresModel.objects.filter(int_array__2=6)
        with self.assertNumQueries(1):
            data13 = [o.int_array for o in qs.all()]
        with self.assertNumQueries(0):
            data14 = [o.int_array for o in qs.all()]
        self.assertListEqual(data14, data13)
        self.assertListEqual(data14, [[4, None, 6]])

        qs = PostgresModel.objects.filter(int_array__0_2=(1, 2))
        with self.assertNumQueries(1):
            data15 = [o.int_array for o in qs.all()]
        with self.assertNumQueries(0):
            data16 = [o.int_array for o in qs.all()]
        self.assertListEqual(data16, data15)
        self.assertListEqual(data16, [[1, 2, 3]])

    def test_hstore(self):
        qs = PostgresModel.objects.all()
        with self.assertNumQueries(1):
            data1 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data2 = [o.hstore for o in qs.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [{'a': 'b', 'c': None},
                                     {'a': '1', 'b': '2'}])

        qs = PostgresModel.objects.filter(hstore__a='1')
        with self.assertNumQueries(1):
            data3 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data4 = [o.hstore for o in qs.all()]
        self.assertListEqual(data4, data3)
        self.assertListEqual(data4, [{'a': '1', 'b': '2'}])

        qs = PostgresModel.objects.filter(
            hstore__contains={'a': 'b'})
        with self.assertNumQueries(1):
            data5 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data6 = [o.hstore for o in qs.all()]
        self.assertListEqual(data6, data5)
        self.assertListEqual(data6, [{'a': 'b', 'c': None}])

        qs = PostgresModel.objects.filter(
            hstore__contained_by={'a': 'b', 'c': None, 'b': '2'})
        with self.assertNumQueries(1):
            data7 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data8 = [o.hstore for o in qs.all()]
        self.assertListEqual(data8, data7)
        self.assertListEqual(data8, [{'a': 'b', 'c': None}])

        qs = PostgresModel.objects.filter(hstore__has_key='c')
        with self.assertNumQueries(1):
            data9 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data10 = [o.hstore for o in qs.all()]
        self.assertListEqual(data10, data9)
        self.assertListEqual(data10, [{'a': 'b', 'c': None}])

        qs = PostgresModel.objects.filter(hstore__has_keys=['a', 'b'])
        with self.assertNumQueries(1):
            data11 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data12 = [o.hstore for o in qs.all()]
        self.assertListEqual(data12, data11)
        self.assertListEqual(data12, [{'a': '1', 'b': '2'}])

        qs = PostgresModel.objects.filter(hstore__keys=['a', 'b'])
        with self.assertNumQueries(1):
            data13 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data14 = [o.hstore for o in qs.all()]
        self.assertListEqual(data14, data13)
        self.assertListEqual(data14, [{'a': '1', 'b': '2'}])

        qs = PostgresModel.objects.filter(hstore__values=['1', '2'])
        with self.assertNumQueries(1):
            data15 = [o.hstore for o in qs.all()]
        with self.assertNumQueries(0):
            data16 = [o.hstore for o in qs.all()]
        self.assertListEqual(data16, data15)
        self.assertListEqual(data16, [{'a': '1', 'b': '2'}])

    @skipUnless(DJANGO_GTE_1_9,
                'JSON field is only available in Django >= 1.9')
    def test_json(self):
        qs = PostgresModel.objects.all()
        with self.assertNumQueries(1):
            data1 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data2 = [o.json for o in qs.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.obj1.json, self.obj2.json])

        # Tests an index.
        qs = PostgresModel.objects.filter(json__0='something')
        with self.assertNumQueries(1):
            data3 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data4 = [o.json for o in qs.all()]
        self.assertListEqual(data4, data3)
        self.assertListEqual(data4, [self.obj2.json])

        qs = PostgresModel.objects.filter(json__0__nonexistent_key='something')
        with self.assertNumQueries(1):
            data5 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data6 = [o.json for o in qs.all()]
        self.assertListEqual(data6, data5)
        self.assertListEqual(data6, [])

        # Tests a path with spaces.
        qs = PostgresModel.objects.filter(
            **{'json__1__e__and yet__another': 'one'})
        with self.assertNumQueries(1):
            data7 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data8 = [o.json for o in qs.all()]
        self.assertListEqual(data8, data7)
        self.assertListEqual(data8, [self.obj2.json])

        qs = PostgresModel.objects.filter(json__contains=['something'])
        with self.assertNumQueries(1):
            data9 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data10 = [o.json for o in qs.all()]
        self.assertListEqual(data10, data9)
        self.assertListEqual(data10, [self.obj2.json])

        qs = PostgresModel.objects.filter(
            json__contained_by={'a': 1, 'b': 2, 'any': 'thing'})
        with self.assertNumQueries(1):
            data11 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data12 = [o.json for o in qs.all()]
        self.assertListEqual(data12, data11)
        self.assertListEqual(data12, [self.obj1.json])

        qs = PostgresModel.objects.filter(json__has_key='a')
        with self.assertNumQueries(1):
            data13 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data14 = [o.json for o in qs.all()]
        self.assertListEqual(data14, data13)
        self.assertListEqual(data14, [self.obj1.json])

        qs = PostgresModel.objects.filter(json__has_any_keys=['a', 'b', 'c'])
        with self.assertNumQueries(1):
            data15 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data16 = [o.json for o in qs.all()]
        self.assertListEqual(data16, data15)
        self.assertListEqual(data16, [self.obj1.json])

        qs = PostgresModel.objects.filter(json__has_keys=['a', 'b'])
        with self.assertNumQueries(1):
            data17 = [o.json for o in qs.all()]
        with self.assertNumQueries(0):
            data18 = [o.json for o in qs.all()]
        self.assertListEqual(data18, data17)
        self.assertListEqual(data18, [self.obj1.json])

    def test_int_range(self):
        qs = PostgresModel.objects.all()
        with self.assertNumQueries(1):
            data1 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data2 = [o.int_range for o in qs.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [NumericRange(1900, 2000),
                                     NumericRange(1989)])

        qs = PostgresModel.objects.filter(int_range__contains=2015)
        with self.assertNumQueries(1):
            data3 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data4 = [o.int_range for o in qs.all()]
        self.assertListEqual(data4, data3)
        self.assertListEqual(data4, [NumericRange(1989)])

        qs = PostgresModel.objects.filter(
            int_range__contains=NumericRange(1950, 1990))
        with self.assertNumQueries(1):
            data5 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data6 = [o.int_range for o in qs.all()]
        self.assertListEqual(data6, data5)
        self.assertListEqual(data6, [NumericRange(1900, 2000)])

        qs = PostgresModel.objects.filter(
            int_range__contained_by=NumericRange(0, 2050))
        with self.assertNumQueries(1):
            data5 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data6 = [o.int_range for o in qs.all()]
        self.assertListEqual(data6, data5)
        self.assertListEqual(data6, [NumericRange(1900, 2000)])

        qs = PostgresModel.objects.filter(int_range__fully_lt=(2015, None))
        with self.assertNumQueries(1):
            data7 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data8 = [o.int_range for o in qs.all()]
        self.assertListEqual(data8, data7)
        self.assertListEqual(data8, [NumericRange(1900, 2000)])

        qs = PostgresModel.objects.filter(int_range__fully_gt=(1970, 1980))
        with self.assertNumQueries(1):
            data9 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data10 = [o.int_range for o in qs.all()]
        self.assertListEqual(data10, data9)
        self.assertListEqual(data10, [NumericRange(1989)])

        qs = PostgresModel.objects.filter(int_range__not_lt=(1970, 1980))
        with self.assertNumQueries(1):
            data11 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data12 = [o.int_range for o in qs.all()]
        self.assertListEqual(data12, data11)
        self.assertListEqual(data12, [NumericRange(1989)])

        qs = PostgresModel.objects.filter(int_range__not_gt=(1970, 1980))
        with self.assertNumQueries(1):
            data13 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data14 = [o.int_range for o in qs.all()]
        self.assertListEqual(data14, data13)
        self.assertListEqual(data14, [])

        qs = PostgresModel.objects.filter(int_range__adjacent_to=(1900, 1989))
        with self.assertNumQueries(1):
            data15 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data16 = [o.int_range for o in qs.all()]
        self.assertListEqual(data16, data15)
        self.assertListEqual(data16, [NumericRange(1989)])

        qs = PostgresModel.objects.filter(int_range__startswith=1900)
        with self.assertNumQueries(1):
            data17 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data18 = [o.int_range for o in qs.all()]
        self.assertListEqual(data18, data17)
        self.assertListEqual(data18, [NumericRange(1900, 2000)])

        qs = PostgresModel.objects.filter(int_range__endswith=2000)
        with self.assertNumQueries(1):
            data19 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data20 = [o.int_range for o in qs.all()]
        self.assertListEqual(data20, data19)
        self.assertListEqual(data20, [NumericRange(1900, 2000)])

        PostgresModel.objects.create(int_range=[1900, 1900])

        qs = PostgresModel.objects.filter(int_range__isempty=True)
        with self.assertNumQueries(1):
            data21 = [o.int_range for o in qs.all()]
        with self.assertNumQueries(0):
            data22 = [o.int_range for o in qs.all()]
        self.assertListEqual(data22, data21)
        self.assertListEqual(data22, [NumericRange(empty=True)])

    def test_float_range(self):
        with self.assertNumQueries(1):
            data1 = [o.float_range for o in PostgresModel.objects.all()]
        with self.assertNumQueries(0):
            data2 = [o.float_range for o in PostgresModel.objects.all()]
        self.assertListEqual(data2, data1)
        # For a strange reason, probably a misconception in psycopg2
        # or a bad name in django.contrib.postgres (less probable),
        # FloatRange returns decimals instead of floats.
        self.assertListEqual(data2, [
            NumericRange(Decimal('-1000.0'), Decimal('9.87654321')),
            NumericRange(Decimal('0.0'))])

    def test_date_range(self):
        with self.assertNumQueries(1):
            data1 = [o.date_range for o in PostgresModel.objects.all()]
        with self.assertNumQueries(0):
            data2 = [o.date_range for o in PostgresModel.objects.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [
            DateRange(date(1678, 3, 4), date(1741, 7, 28)),
            DateRange(date(1989, 1, 30))])

    def test_datetime_range(self):
        with self.assertNumQueries(1):
            data1 = [o.datetime_range for o in PostgresModel.objects.all()]
        with self.assertNumQueries(0):
            data2 = [o.datetime_range for o in PostgresModel.objects.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [
            DateTimeTZRange(datetime(1989, 1, 30, 12, 20,
                                     tzinfo=timezone('Europe/Paris'))),
            DateTimeTZRange(bounds='()')])

    @skipUnless(DJANGO_GTE_1_9,
                'TransactionNow is only available in Django >= 1.9')
    def test_transaction_now(self):
        """
        Checks that queries with a TransactionNow() parameter are not cached.
        """
        obj = Test.objects.create(datetime='1992-07-02T12:00:00')
        qs = Test.objects.filter(
            datetime__lte=TransactionNow())
        with self.assertNumQueries(1):
            obj1 = qs.get()
        with self.assertNumQueries(1):
            obj2 = qs.get()
        self.assertEqual(obj1, obj2)
        self.assertEqual(obj1, obj)
