# coding: utf-8

from __future__ import unicode_literals
import datetime
from decimal import Decimal
from hashlib import sha1
from time import time
from uuid import UUID

from django.contrib.postgres.functions import TransactionNow
from django.db import connections
from django.db.models import QuerySet, Subquery, Exists
from django.db.models.functions import Now
from django.db.models.sql import Query, AggregateQuery
from django.db.models.sql.where import ExtraWhere, WhereNode
from django.utils.six import text_type, binary_type, integer_types

from .settings import ITERABLES, cachalot_settings
from .transaction import AtomicCache


class UncachableQuery(Exception):
    pass


class IsRawQuery(Exception):
    pass


CACHABLE_PARAM_TYPES = {
    bool, int, float, Decimal, bytearray, binary_type, text_type, type(None),
    datetime.date, datetime.time, datetime.datetime, datetime.timedelta, UUID,
}
CACHABLE_PARAM_TYPES.update(integer_types)  # Adds long for Python 2
UNCACHABLE_FUNCS = {Now, TransactionNow}

try:
    from psycopg2 import Binary
    from psycopg2.extras import (
        NumericRange, DateRange, DateTimeRange, DateTimeTZRange, Inet, Json)
    from django.contrib.postgres.fields.jsonb import JsonAdapter

except ImportError:
    pass
else:
    CACHABLE_PARAM_TYPES.update((
        Binary, NumericRange, DateRange, DateTimeRange, DateTimeTZRange, Inet,
        Json, JsonAdapter))


def check_parameter_types(params):
    for p in params:
        cl = p.__class__
        if cl not in CACHABLE_PARAM_TYPES:
            if cl in ITERABLES:
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
    cache_key = '%s:%s:%s' % (compiler.using, sql,
                              [text_type(p) for p in params])
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


def _get_tables_from_sql(connection, lowercased_sql):
    return {t for t in connection.introspection.django_table_names()
            if t in lowercased_sql}


def _find_subqueries_in_where(children):
    for child in children:
        child_class = child.__class__
        if child_class is WhereNode:
            for grand_child in _find_subqueries_in_where(child.children):
                yield grand_child
        elif child_class is ExtraWhere:
            raise IsRawQuery
        else:
            rhs = child.rhs
            rhs_class = rhs.__class__
            if rhs_class is Query:
                yield rhs
            elif rhs_class is QuerySet:
                yield rhs.query
            elif rhs_class is Subquery or rhs_class is Exists:
                yield rhs.queryset.query
            elif rhs_class in UNCACHABLE_FUNCS:
                raise UncachableQuery


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


def _get_tables(db_alias, query):
    if query.select_for_update or (
            not cachalot_settings.CACHALOT_CACHE_RANDOM
            and '?' in query.order_by):
        raise UncachableQuery

    try:
        if query.extra_select:
            raise IsRawQuery
        # Gets all tables already found by the ORM.
        tables = set(query.table_map)
        tables.add(query.get_meta().db_table)
        # Gets tables in subquery annotations.
        for annotation in query.annotations.values():
            if isinstance(annotation, Subquery):
                tables.update(_get_tables(db_alias, annotation.queryset.query))
        # Gets tables in WHERE subqueries.
        for subquery in _find_subqueries_in_where(query.where.children):
            tables.update(_get_tables(db_alias, subquery))
        # Gets tables in HAVING subqueries.
        if isinstance(query, AggregateQuery):
            tables.update(
                _get_tables_from_sql(connections[db_alias], query.subquery))
        # Gets tables in combined queries
        # using `.union`, `.intersection`, or `difference`.
        if query.combined_queries:
            for combined_query in query.combined_queries:
                tables.update(_get_tables(db_alias, combined_query))
    except IsRawQuery:
        sql = query.get_compiler(db_alias).as_sql()[0].lower()
        tables = _get_tables_from_sql(connections[db_alias], sql)

    if not are_all_cachable(tables):
        raise UncachableQuery
    return tables


def _get_table_cache_keys(compiler):
    db_alias = compiler.using
    get_table_cache_key = cachalot_settings.CACHALOT_TABLE_KEYGEN
    return [get_table_cache_key(db_alias, t)
            for t in _get_tables(db_alias, compiler.query)]


def _invalidate_tables(cache, db_alias, tables):
    tables = filter_cachable(set(tables))
    if not tables:
        return
    now = time()
    get_table_cache_key = cachalot_settings.CACHALOT_TABLE_KEYGEN
    cache.set_many(
        {get_table_cache_key(db_alias, t): now for t in tables},
        cachalot_settings.CACHALOT_TIMEOUT)

    if isinstance(cache, AtomicCache):
        cache.to_be_invalidated.update(tables)
