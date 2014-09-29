# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
import re

from django.core.cache import cache as django_cache
from django.db import connection
from django.db.models.query import EmptyResultSet
from django.db.models.sql.compiler import (
    SQLCompiler, SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
    SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
from django.db.models.sql.where import ExtraWhere
from django.db.transaction import Atomic


COMPILERS = (SQLCompiler,
             SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
             SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
READ_COMPILERS = [c for c in COMPILERS if c not in WRITE_COMPILERS]


PATCHED = False
MISS_VALUE = '[[Missing cache key]]'


def _get_tables(query):
    """
    Returns a ``set`` of all database table names used by ``query``.
    """
    tables = set(query.tables)
    tables.add(query.model._meta.db_table)
    return tables


def _get_tables_cache_keys(query):
    return ['%s_queries' % t for t in _get_tables(query)]


def _update_tables_queries(cache, query, cache_key):
    tables_cache_keys = _get_tables_cache_keys(query)
    tables_queries = cache.get_many(tables_cache_keys)
    for k in tables_cache_keys:
        queries = tables_queries.get(k, [])
        queries.append(cache_key)
        tables_queries[k] = queries
    cache.set_many(tables_queries)


def _invalidate_tables(cache, query):
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


TRANSACTION_CACHES = []


class AtomicCache(dict):
    def __init__(self):
        super(AtomicCache, self).__init__()
        self.parent_cache = (TRANSACTION_CACHES[-1] if TRANSACTION_CACHES
                             else django_cache)
        self.to_be_deleted = set()

    def get(self, k, default=None):
        if k in self.to_be_deleted:
            return default
        if k in self:
            return self[k]
        return self.parent_cache.get(k, default)

    def set(self, k, v):
        if k in self.to_be_deleted:
            self.to_be_deleted.remove(k)
        self[k] = v

    def delete(self, k):
        self.to_be_deleted.add(k)

    def get_many(self, keys):
        data = {}
        for k in keys:
            v = self.get(k, MISS_VALUE)
            if v != MISS_VALUE:
                data[k] = v
        return data

    def set_many(self, data):
        self.to_be_deleted.difference_update(set(data))
        self.update(data)

    def delete_many(self, keys):
        self.to_be_deleted.update(keys)

    def commit(self):
        self.parent_cache.set_many(self)
        self.parent_cache.delete_many(self.to_be_deleted)

    def __repr__(self):
        return '<AtomicCache (cache=%s, to_be_deleted=%s)>' % (
            super(AtomicCache, self).__repr__(),
            self.to_be_deleted)


def get_cache():
    if TRANSACTION_CACHES:
        return TRANSACTION_CACHES[-1]
    return django_cache


def _patch_orm_read():
    def patch_execute_sql(original):
        def inner(compiler, *args, **kwargs):
            if isinstance(compiler, WRITE_COMPILERS):
                return original(compiler, *args, **kwargs)

            query = compiler.query

            if _has_extra_select_or_where(query):
                return original(compiler, *args, **kwargs)

            try:
                cache_key = compiler.as_sql()
            except EmptyResultSet:
                return original(compiler, *args, **kwargs)

            cache = get_cache()
            result = cache.get(cache_key, MISS_VALUE)

            if result == MISS_VALUE:
                result = original(compiler, *args, **kwargs)
                if isinstance(result, Iterable) \
                        and not isinstance(result, (tuple, list)):
                    result = list(result)

                _update_tables_queries(cache, query, cache_key)

                cache.set(cache_key, result)

            return result

        inner.original = original
        return inner

    for compiler in READ_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def _patch_orm_write():
    def patch_execute_sql(original):
        def inner(compiler, *args, **kwargs):
            _invalidate_tables(get_cache(), compiler.query)
            return original(compiler, *args, **kwargs)

        inner.original = original
        return inner

    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def _patch_atomic():
    def patch_enter(original):
        def inner(self):
            TRANSACTION_CACHES.append(AtomicCache())
            original(self)

        inner.original = original
        return inner

    def patch_exit(original):
        def inner(self, exc_type, exc_value, traceback):
            atomic_cache = TRANSACTION_CACHES.pop()
            if exc_type is None and not connection.needs_rollback:
                atomic_cache.commit()

            original(self, exc_type, exc_value, traceback)

        inner.original = original
        return inner

    Atomic.__enter__ = patch_enter(Atomic.__enter__)
    Atomic.__exit__ = patch_exit(Atomic.__exit__)


def _unpatch_orm_read():
    for compiler in READ_COMPILERS:
        compiler.execute_sql = compiler.execute_sql.original


def _unpatch_orm_write():
    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = compiler.execute_sql.original


def _unpatch_atomic():
    Atomic.__enter__ = Atomic.__enter__.original
    Atomic.__exit__ = Atomic.__exit__.original


def _patch_test_db():
    def patch(original):
        def inner(*args, **kwargs):
            django_cache.clear()
            return original(*args, **kwargs)

        inner.original = original
        return inner

    creation = connection.creation
    creation.create_test_db = patch(creation.create_test_db)
    creation.destroy_test_db = patch(creation.destroy_test_db)


def _unpatch_test_db():
    creation = connection.creation
    creation.create_test_db = creation.create_test_db.original
    creation.destroy_test_db = creation.destroy_test_db.original


def patch():
    global PATCHED
    _patch_test_db()
    _patch_orm_write()
    _patch_orm_read()
    _patch_atomic()
    PATCHED = True


def unpatch():
    global PATCHED
    _unpatch_test_db()
    _unpatch_orm_read()
    _unpatch_orm_write()
    _unpatch_atomic()
    PATCHED = False


def is_patched():
    return PATCHED
