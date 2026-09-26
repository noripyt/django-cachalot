import re

from django.db import connection
from django.test import SimpleTestCase, override_settings

from ..utils import _get_tables_from_sql


TABLES = [
    'cachalot_test',
    'cachalot_testparent',
    'cachalot_test_extra',
    'cachalot_test2',
    'xcachalot_test',
    'clémentine',
    'my-table',
    'my.table',
    '"public"."cachalot_schema"',
    'ab_c',
    'c_de',
]

BARE_FORMS = [
    'select * from {n} where 1 = 1',
    'select * from public.{n} where 1 = 1',
    'select * from ({n})',
    'select * from x, {n}, y',
    'select *\nfrom\t{n}\nwhere 1 = 1',
    'select {n}.id from {n}',
    'select t1.id from {n} t1',
    'select 1 from a inner join {n} on ({n}.id = a.id)',
    'insert into {n} (name) values (%s)',
    'update {n} set name = %s',
    'delete from {n} where id = %s',
]
QUOTED_FORMS = [
    'select * from {q} where 1 = 1',
    'select * from{q}where 1 = 1',
    'select {q}.id from {q}',
    'select 1 from a inner join {q} on ({q}.id = a.id)',
    'insert into {q} (name) values (%s)',
]
EMBEDDED_FORMS = [
    'select * from {n}_archive',
    'select * from x{n}',
    'select * from x{n}y',
    'select a.{n}_id from a',
    'select count(*) as {n}_count from a',
    'select 1 from a where a.kind = \'{n}_x\'',
    'select 1 from a where a.kind = \'x{n}\'',
]


@override_settings(CACHALOT_ADDITIONAL_TABLES=TABLES)
class TablesFromSQLTestCase(SimpleTestCase):
    """
    Tests that table names are found in raw SQL as whole identifiers only.
    """

    def sql_forms(self, table):
        quoted = connection.ops.quote_name(table)
        for form in BARE_FORMS:
            yield form.format(n=table), False
        for form in QUOTED_FORMS:
            yield form.format(q=quoted), False
            yield form.format(q=quoted), True

    def embedded_sql_forms(self, table):
        for form in EMBEDDED_FORMS:
            sql = form.format(n=table)
            yield sql, False
            yield sql, True

    def get_tables(self, sql, enable_quote):
        return _get_tables_from_sql(connection, sql.lower(), enable_quote)

    def test_table_is_detected(self):
        for table in TABLES:
            for sql, enable_quote in self.sql_forms(table):
                with self.subTest(table=table, sql=sql,
                                  enable_quote=enable_quote):
                    self.assertIn(table, self.get_tables(sql, enable_quote))

    def test_other_tables_are_not_detected(self):
        for table in TABLES:
            for sql, enable_quote in self.sql_forms(table):
                with self.subTest(table=table, sql=sql,
                                  enable_quote=enable_quote):
                    tables = self.get_tables(sql, enable_quote)
                    self.assertEqual(tables & set(TABLES), {table})

    def test_embedded_table_is_not_detected(self):
        for table in TABLES:
            if not re.match(r'^\w+$', table):
                continue
            for sql, enable_quote in self.embedded_sql_forms(table):
                with self.subTest(table=table, sql=sql,
                                  enable_quote=enable_quote):
                    self.assertNotIn(table, self.get_tables(sql, enable_quote))

    def test_overlapping_names_are_not_detected(self):
        for enable_quote in (False, True):
            with self.subTest(enable_quote=enable_quote):
                tables = self.get_tables('select * from ab_c_de', enable_quote)
                self.assertEqual(tables & set(TABLES), set())
