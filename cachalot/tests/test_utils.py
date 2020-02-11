from django import VERSION as DJANGO_VERSION
from django.core.management.color import no_style
from django.db import connection, transaction
try:
    from django.utils.six import string_types
except ImportError:
    from six import string_types

from .models import PostgresModel
from ..utils import _get_tables


class TestUtilsMixin:
    def setUp(self):
        self.is_sqlite = connection.vendor == 'sqlite'
        self.is_mysql = connection.vendor == 'mysql'
        self.is_postgresql = connection.vendor == 'postgresql'
        self.force_repoen_connection()

    # TODO: Remove this workaround when this issue is fixed:
    #       https://code.djangoproject.com/ticket/29494
    def tearDown(self):
        if connection.vendor == 'postgresql':
            flush_sql_list = connection.ops.sql_flush(
                no_style(), (PostgresModel._meta.db_table,), ())
            with transaction.atomic():
                for sql in flush_sql_list:
                    with connection.cursor() as cursor:
                        cursor.execute(sql)

    def force_repoen_connection(self):
        if connection.vendor in ('mysql', 'postgresql'):
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

    def assert_tables(self, queryset, *tables):
        tables = {table if isinstance(table, string_types)
                  else table._meta.db_table for table in tables}
        self.assertSetEqual(_get_tables(queryset.db, queryset.query), tables)

    def assert_query_cached(self, queryset, result=None, result_type=None,
                            compare_results=True, before=1, after=0):
        if result_type is None:
            result_type = list if result is None else type(result)
        with self.assertNumQueries(before):
            data1 = queryset.all()
            if result_type is list:
                data1 = list(data1)
        with self.assertNumQueries(after):
            data2 = queryset.all()
            if result_type is list:
                data2 = list(data2)
        if not compare_results:
            return
        assert_functions = {
            list: self.assertListEqual,
            set: self.assertSetEqual,
            dict: self.assertDictEqual,
        }
        assert_function = assert_functions.get(result_type, self.assertEqual)
        assert_function(data2, data1)
        if result is not None:
            assert_function(data2, result)

    def is_dj_21_below_and_is_sqlite(self):
        """
        Checks if Django 2.1 or lower and if SQLite is the DB
        Django 2.1 and lower had two queries on SQLite DBs:

        After an insertion, e.g. Test.objects.create(name="asdf"),
        SQLite returns the queries:
        [{'sql': 'INSERT INTO "cachalot_test" ("name") VALUES (\'asd\')', 'time': '0.001'}, {'sql': 'BEGIN', 'time': '0.000'}]

        This can be seen with django.db import connection; print(connection.queries)
        In Django 2.2 and above, the latter was removed.

        :return: bool is Django 2.1 or below and is SQLite the DB
        """
        django_version = DJANGO_VERSION
        if not self.is_sqlite:
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
