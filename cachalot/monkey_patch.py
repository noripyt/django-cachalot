# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
import re

from django.core.cache import cache
from django.db.models.query import EmptyResultSet
from django.db.models.sql.compiler import (
    SQLCompiler, SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
    SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
from django.db.models.sql.where import ExtraWhere


COMPILERS = (SQLCompiler,
             SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
             SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
READ_COMPILERS = [c for c in COMPILERS if c not in WRITE_COMPILERS]


PATCHED = False
MISS_VALUE = '[[The cache key was missed]]'


def _get_tables(query):
    """
    Returns a ``set`` of all database table names used by ``query``.
    """
    tables = set(query.tables)
    tables.add(query.model._meta.db_table)
    return tables


def _get_tables_cache_keys(query):
    return ['%s_queries' % t for t in _get_tables(query)]


def _update_tables_queries(query, cache_key):
    tables_cache_keys = _get_tables_cache_keys(query)
    tables_queries = cache.get_many(tables_cache_keys)
    for k in tables_cache_keys:
        queries = tables_queries.get(k, [])
        queries.append(cache_key)
        tables_queries[k] = queries
    cache.set_many(tables_queries)


def _invalidate_tables(query):
    tables_cache_keys = _get_tables_cache_keys(query)
    tables_queries = cache.get_many(tables_cache_keys)
    queries = []
    for k in tables_cache_keys:
        queries.extend(tables_queries.get(k, []))
    cache.delete_many(queries)
    cache.delete_many(tables_cache_keys)


COLUMN_RE = re.compile(r'^"(?P<table>[\w_]+)"\."(?P<column>[\w_]+)"$')


def _has_extra_select_or_where(query):
    """
    Returns True if ``query`` contains a ``QuerySet.extra`` with ``select``
    or ``where`` arguments.

    We also have to check for ``prefetch_related``, as it internally uses a
    ``QuerySet.extra(select={'_prefetch_related_val_…': '"table"."column"'})``.

    For more details on how prefetch_related uses ``QuerySet.extra``, see:
    https://github.com/django/django/blob/1.6.7/django/db/models/fields/related.py#L553-L577
    """

    # Checks if there’s an extra where
    if any(isinstance(child, ExtraWhere) for child in query.where.children):
        return True

    # Checks if there’s an extra select
    if query.extra_select and query.extra_select_mask is None:
        tables = _get_tables(query)
        # Checks if extra subqueries are something else than one or several
        # ``prefetch_related``.
        for subquery, params in query.extra_select.values():
            match = COLUMN_RE.match(subquery)
            return match is None or match.group('table') not in tables
    return False


def _monkey_patch_orm_read():
    def patch_execute_sql(method):
        def inner(compiler, *args, **kwargs):
            if isinstance(compiler, WRITE_COMPILERS):
                return method(compiler, *args, **kwargs)

            query = compiler.query

            if _has_extra_select_or_where(query):
                return method(compiler, *args, **kwargs)

            try:
                cache_key = compiler.as_sql()
            except EmptyResultSet:
                return method(compiler, *args, **kwargs)

            result = cache.get(cache_key, MISS_VALUE)

            if result == MISS_VALUE:
                result = method(compiler, *args, **kwargs)
                if isinstance(result, Iterable) \
                        and not isinstance(result, (tuple, list)):
                    result = list(result)

                _update_tables_queries(query, cache_key)

                cache.set(cache_key, result)

            return result

        return inner

    for compiler in READ_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def _monkey_patch_orm_write():
    def patch_execute_sql(method):
        def inner(compiler, *args, **kwargs):
            _invalidate_tables(compiler.query)
            return method(compiler, *args, **kwargs)
        return inner

    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def monkey_patch_orm():
    global PATCHED
    _monkey_patch_orm_write()
    _monkey_patch_orm_read()
    PATCHED = True


def is_patched():
    return PATCHED
