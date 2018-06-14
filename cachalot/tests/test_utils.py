from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils.six import string_types

from .models import PostgresModel
from ..utils import _get_tables


class TestUtilsMixin:
    def setUp(self):
        self.is_sqlite = connection.vendor == 'sqlite'
        self.is_mysql = connection.vendor == 'mysql'
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
