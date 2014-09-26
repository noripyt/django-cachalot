# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
from django.core.cache import cache
from django.db.models.query import EmptyResultSet
from django.db.models.sql.compiler import (
    SQLCompiler, SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
    SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)


COMPILERS = (SQLCompiler,
             SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
             SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
READ_COMPILERS = [c for c in COMPILERS if c not in WRITE_COMPILERS]


PATCHED = False
MISS_VALUE = '[[The cache key was missed]]'


def _get_tables_cache_keys(compiler):
    q = compiler.query
    # FIXME: `.extra` (and maybe more) are not in alias_map
    tables = q.alias_map.keys()

    return ['%s_queries' % t for t in tables]


def _update_tables_queries(compiler, cache_key):
    tables_cache_keys = _get_tables_cache_keys(compiler)
    tables_queries = cache.get_many(tables_cache_keys)
    for k in tables_cache_keys:
        queries = tables_queries.get(k, [])
        queries.append(cache_key)
        tables_queries[k] = queries
    cache.set_many(tables_queries)


def _invalidate_tables(compiler):
    tables_cache_keys = _get_tables_cache_keys(compiler)
    tables_queries = cache.get_many(tables_cache_keys)
    queries = []
    for k in tables_cache_keys:
        queries.extend(tables_queries.get(k, []))
    cache.delete_many(queries)
    cache.delete_many(tables_cache_keys)


def _monkey_patch_orm_read():
    def patch_execute_sql(method):
        def inner(compiler, *args, **kwargs):
            if isinstance(compiler, WRITE_COMPILERS):
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

                _update_tables_queries(compiler, cache_key)

                cache.set(cache_key, result)

            return result

        return inner

    for compiler in READ_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def _monkey_patch_orm_write():
    def patch_execute_sql(method):
        def inner(compiler, *args, **kwargs):
            _invalidate_tables(compiler)
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
