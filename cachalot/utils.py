# coding: utf-8

from __future__ import unicode_literals
import datetime
from decimal import Decimal
from hashlib import sha1
from time import time
from uuid import UUID

from django import VERSION as django_version
from django.db import connections
from django.db.models.sql import Query
from django.db.models.sql.where import ExtraWhere, SubqueryConstraint
from django.utils.module_loading import import_string
from django.utils.six import text_type, binary_type

from .settings import cachalot_settings
from .transaction import AtomicCache


DJANGO_GTE_1_9 = django_version[:2] >= (1, 9)


class UncachableQuery(Exception):
    pass


TUPLE_OR_LIST = {tuple, list}

CACHABLE_PARAM_TYPES = {
    bool, int, float, Decimal, binary_type, text_type, type(None),
    datetime.date, datetime.time, datetime.datetime, datetime.timedelta, UUID,
}

UNCACHABLE_FUNCS = set()
if DJANGO_GTE_1_9:
    from django.db.models.functions import Now
    from django.contrib.postgres.functions import TransactionNow
    UNCACHABLE_FUNCS.update((Now, TransactionNow))

try:
    from psycopg2.extras import (
        NumericRange, DateRange, DateTimeRange, DateTimeTZRange, Inet, Json)
except ImportError:
    pass
else:
    CACHABLE_PARAM_TYPES.update((
        NumericRange, DateRange, DateTimeRange, DateTimeTZRange, Inet, Json))


def check_parameter_types(params):
    for p in params:
        cl = p.__class__
        if cl not in CACHABLE_PARAM_TYPES:
            if cl in TUPLE_OR_LIST:
                check_parameter_types(p)
            elif cl is dict:
                check_parameter_types(p.items())
            else:
                raise UncachableQuery


def get_query_cache_key(compiler):
    """
    Generates a cache key from a SQLCompiler.

    This cache key is specific to the SQL query and its context
    (which database is used).  The same query in the same context
    (= the same database) must generate the same cache key.

    :arg compiler: A SQLCompiler that will generate the SQL query
    :type compiler: django.db.models.sql.compiler.SQLCompiler
    :return: A cache key
    :rtype: int
    """
    sql, params = compiler.as_sql()
    check_parameter_types(params)
    cache_key = '%s:%s:%s' % (compiler.using, sql, params)
    return sha1(cache_key.encode('utf-8')).hexdigest()


def get_table_cache_key(db_alias, table):
    """
    Generates a cache key from a SQL table.

    :arg db_alias: Alias of the used database
    :type db_alias: str or unicode
    :arg table: Name of the SQL table
    :type table: str or unicode
    :return: A cache key
    :rtype: int
    """
    cache_key = '%s:%s' % (db_alias, table)
    return sha1(cache_key.encode('utf-8')).hexdigest()


def _get_query_cache_key(compiler):
    return import_string(cachalot_settings.CACHALOT_QUERY_KEYGEN)(compiler)


def _get_table_cache_key(db_alias, table):
    return import_string(cachalot_settings.CACHALOT_TABLE_KEYGEN)(db_alias, table)


def _get_tables_from_sql(connection, lowercased_sql):
    return [t for t in connection.introspection.django_table_names()
            if t in lowercased_sql]


def _find_subqueries(children):
    for child in children:
        if child.__class__ is SubqueryConstraint:
            if child.query_object.__class__ is Query:
                yield child.query_object
            else:
                yield child.query_object.query
        else:
            rhs = None
            if hasattr(child, 'rhs'):
                rhs = child.rhs
            rhs_class = rhs.__class__
            if rhs_class is Query:
                yield rhs
            elif hasattr(rhs, 'query'):
                yield rhs.query
            elif rhs_class in UNCACHABLE_FUNCS:
                raise UncachableQuery
        if hasattr(child, 'children'):
            for grand_child in _find_subqueries(child.children):
                yield grand_child


def is_cachable(table):
    whitelist = cachalot_settings.CACHALOT_ONLY_CACHABLE_TABLES
    if whitelist and table not in whitelist:
        return False
    return table not in cachalot_settings.CACHALOT_UNCACHABLE_TABLES


def are_all_cachable(tables):
    whitelist = cachalot_settings.CACHALOT_ONLY_CACHABLE_TABLES
    if whitelist and not tables.issubset(whitelist):
        return False
    return tables.isdisjoint(cachalot_settings.CACHALOT_UNCACHABLE_TABLES)


def filter_cachable(tables):
    whitelist = cachalot_settings.CACHALOT_ONLY_CACHABLE_TABLES
    tables = tables.difference(cachalot_settings.CACHALOT_UNCACHABLE_TABLES)
    if whitelist:
        return tables.intersection(whitelist)
    return tables


def _get_tables(query, db_alias):
    if ('?' in query.order_by and not cachalot_settings.CACHALOT_CACHE_RANDOM) \
            or query.select_for_update:
        raise UncachableQuery

    tables = set(query.table_map)
    tables.add(query.get_meta().db_table)
    subquery_constraints = _find_subqueries(query.where.children)
    for subquery in subquery_constraints:
        tables.update(_get_tables(subquery, db_alias))
    if query.extra_select or hasattr(query, 'subquery') \
            or any(c.__class__ is ExtraWhere for c in query.where.children):
        sql = query.get_compiler(db_alias).as_sql()[0].lower()
        additional_tables = _get_tables_from_sql(connections[db_alias], sql)
        tables.update(additional_tables)

    if not are_all_cachable(tables):
        raise UncachableQuery
    return tables


def _get_table_cache_keys(compiler):
    db_alias = compiler.using
    return [_get_table_cache_key(db_alias, t)
            for t in _get_tables(compiler.query, db_alias)]


def _invalidate_tables(cache, db_alias, tables):
    tables = filter_cachable(set(tables))
    if not tables:
        return
    now = time()
    cache.set_many(
        {_get_table_cache_key(db_alias, t): now for t in tables},
        cachalot_settings.CACHALOT_TIMEOUT)

    if isinstance(cache, AtomicCache):
        cache.to_be_invalidated.update(tables)
