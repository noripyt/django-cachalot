from django.db import connection

from ..utils import _get_tables


class TestUtilsMixin:
    def setUp(self):
        self.is_sqlite = connection.vendor == 'sqlite'
        self.is_mysql = connection.vendor == 'mysql'
        self.force_repoen_connection()

    def force_repoen_connection(self):
        if connection.vendor in ('mysql', 'postgresql'):
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

    def assert_tables(self, queryset, *tables):
        self.assertSetEqual(_get_tables(queryset.db, queryset.query),
                            set(tables))

    def assert_query_cached(self, queryset, result=None, result_type=None,
                            compare_results=True, before=1, after=0):
        with self.assertNumQueries(before):
            data1 = list(queryset.all())
        with self.assertNumQueries(after):
            data2 = list(queryset.all())
        if not compare_results:
            return
        if result_type is None:
            result_type = list if result is None else type(result)
        assert_functions = {
            list: self.assertListEqual,
            set: self.assertSetEqual,
            dict: self.assertDictEqual,
        }
        assert_function = assert_functions.get(result_type, self.assertEqual)
        assert_function(data2, data1)
        if result is not None:
            assert_function(data2, result)
