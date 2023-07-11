from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connection, connections, transaction

from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from ..utils import _get_tables
from .models import PostgresModel


class TestUtilsMixin:
    def setUp(self):
        self.is_sqlite = connection.vendor == 'sqlite'
        self.is_mysql = connection.vendor == 'mysql'
        self.is_postgresql = connection.vendor == 'postgresql'
        self.force_reopen_connection()

    # TODO: Remove this workaround when this issue is fixed:
    #       https://code.djangoproject.com/ticket/29494
    def tearDown(self):
        if connection.vendor == 'postgresql':
            flush_args = [no_style(), (PostgresModel._meta.db_table,),]
            flush_sql_list = connection.ops.sql_flush(*flush_args)
            with transaction.atomic():
                for sql in flush_sql_list:
                    with connection.cursor() as cursor:
                        cursor.execute(sql)

    def force_reopen_connection(self):
        if connection.vendor in ('mysql', 'postgresql'):
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

    def assert_tables(self, queryset, *tables):
        tables = {table if isinstance(table, str)
                  else table._meta.db_table for table in tables}
        self.assertSetEqual(_get_tables(queryset.db, queryset.query), tables, str(queryset.query))

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

class FilteredTransactionTestCase(TransactionTestCase):
    """
    TransactionTestCase with assertNumQueries that ignores BEGIN, COMMIT and ROLLBACK
    queries.
    """
    def assertNumQueries(self, num, func=None, *args, using=DEFAULT_DB_ALIAS, **kwargs):
        conn = connections[using]

        context = FilteredAssertNumQueriesContext(self, num, conn)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)


class FilteredAssertNumQueriesContext(CaptureQueriesContext):
    """
    Capture queries and assert their number ignoring BEGIN, COMMIT and ROLLBACK queries.
    """
    EXCLUDE = ('BEGIN', 'COMMIT', 'ROLLBACK')

    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        super().__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return

        filtered_queries = []
        excluded_queries = []
        for q in self.captured_queries:
            if q['sql'].upper() not in self.EXCLUDE:
                filtered_queries.append(q)
            else:
                excluded_queries.append(q)

        executed = len(filtered_queries)

        self.test_case.assertEqual(
            executed,
            self.num,
            f"\n{executed} queries executed on {self.connection.vendor}, {self.num} expected\n" +
            "\nCaptured queries were:\n" +
            "".join(
                f"{i}. {query['sql']}\n"
                for i, query in enumerate(filtered_queries, start=1)
            ) +
            "\nCaptured queries, that were excluded:\n" +
            "".join(
                f"{i}. {query['sql']}\n"
                for i, query in enumerate(excluded_queries, start=1)
            )
        )
