# coding: utf-8

from __future__ import unicode_literals
from collections import defaultdict, Iterable
from functools import wraps
from hashlib import md5
import pickle
import re

from django.conf import settings
# TODO: Replace with caches[CACHALOT_CACHE] when we drop Django 1.6 support.
from django.core.cache import get_cache as get_django_cache
from django.db import connection
from django.db.models.query import EmptyResultSet
from django.db.models.sql.compiler import (
    SQLCompiler, SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
    SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
from django.db.models.sql.where import ExtraWhere
from django.db.transaction import Atomic
from django.test import TransactionTestCase

from .settings import cachalot_settings


COMPILERS = (SQLCompiler,
             SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
             SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
READ_COMPILERS = [c for c in COMPILERS if c not in WRITE_COMPILERS]


PATCHED = False


def hash_cache_key(unicode_key):
    return md5(unicode_key.encode('utf-8')).hexdigest()


def _get_query_cache_key(compiler):
    return hash_cache_key('%s:%s' % compiler.as_sql())


def _get_tables(query):
    """
    Returns a ``set`` of all database table names used by ``query``.
    """
    tables = set(query.tables)
    tables.add(query.model._meta.db_table)
    return tables


def _get_table_cache_key(table):
    return hash_cache_key('%s_queries' % table)


def _get_tables_cache_keys(query):
    return [_get_table_cache_key(t) for t in _get_tables(query)]


def _update_tables_queries(cache, query, cache_key):
    tables_cache_keys = _get_tables_cache_keys(query)
    tables_queries = cache.get_many(tables_cache_keys)
    for k in tables_cache_keys:
        queries = tables_queries.get(k, [])
        queries.append(cache_key)
        tables_queries[k] = queries
    cache.set_many(tables_queries)


def _invalidate_tables_cache_keys(cache, tables_cache_keys):
    tables_queries = cache.get_many(tables_cache_keys)
    queries = [q for k in tables_cache_keys for q in tables_queries.get(k, [])]
    cache.delete_many(queries + tables_cache_keys)


def _invalidate_tables(cache, query):
    tables_cache_keys = _get_tables_cache_keys(query)
    _invalidate_tables_cache_keys(cache, tables_cache_keys)


def clear_cache(cache):
    tables = connection.introspection.table_names()
    tables_cache_keys = [_get_table_cache_key(t) for t in tables]
    _invalidate_tables_cache_keys(cache, tables_cache_keys)


def clear_all_caches():
    for cache in settings.CACHES:
        clear_cache(get_django_cache(cache))


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


NESTED_CACHES = defaultdict(list)


class AtomicCache(dict):
    def __init__(self):
        super(AtomicCache, self).__init__()
        self.parent_cache = get_cache()
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
        data = dict([(k, self[k]) for k in keys if
                     k in self and k not in self.to_be_deleted])
        missing_keys = set(keys)
        missing_keys.difference_update(data)
        data.update(self.parent_cache.get_many(missing_keys))
        return data

    def set_many(self, data):
        self.to_be_deleted.difference_update(data)
        self.update(data)

    def delete_many(self, keys):
        self.to_be_deleted.update(keys)

    def commit(self):
        self.parent_cache.set_many(self)
        self.parent_cache.delete_many(self.to_be_deleted)


def get_cache():
    cache_name = cachalot_settings.CACHALOT_CACHE
    nested_caches = NESTED_CACHES[cache_name]
    if nested_caches:
        return nested_caches[-1]
    return get_django_cache(cache_name)


def _patch_orm_read():
    def patch_execute_sql(original):
        @wraps(original)
        def inner(compiler, *args, **kwargs):
            if not cachalot_settings.CACHALOT_ENABLED \
                    or isinstance(compiler, WRITE_COMPILERS):
                return original(compiler, *args, **kwargs)

            query = compiler.query

            if _has_extra_select_or_where(query):
                return original(compiler, *args, **kwargs)

            try:
                cache_key = _get_query_cache_key(compiler)
            except EmptyResultSet:
                return original(compiler, *args, **kwargs)

            cache = get_cache()
            result = cache.get(cache_key)

            if result is None:
                result = original(compiler, *args, **kwargs)
                if isinstance(result, Iterable) \
                        and not isinstance(result, (tuple, list)):
                    result = list(result)

                _update_tables_queries(cache, query, cache_key)

                cache.set(cache_key, pickle.dumps(result))
            else:
                result = pickle.loads(result)

            return result

        inner.original = original
        return inner

    for compiler in READ_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def _patch_orm_write():
    def patch_execute_sql(original):
        @wraps(original)
        def inner(compiler, *args, **kwargs):
            _invalidate_tables(get_cache(), compiler.query)
            return original(compiler, *args, **kwargs)

        inner.original = original
        return inner

    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def _patch_atomic():
    def patch_enter(original):
        @wraps(original)
        def inner(self):
            nested_caches = NESTED_CACHES[cachalot_settings.CACHALOT_CACHE]
            nested_caches.append(AtomicCache())
            original(self)

        inner.original = original
        return inner

    def patch_exit(original):
        @wraps(original)
        def inner(self, exc_type, exc_value, traceback):
            needs_rollback = connection.needs_rollback

            original(self, exc_type, exc_value, traceback)

            nested_caches = NESTED_CACHES[cachalot_settings.CACHALOT_CACHE]
            atomic_cache = nested_caches.pop()
            if exc_type is None and not needs_rollback:
                atomic_cache.commit()

        inner.original = original
        return inner

    Atomic.__enter__ = patch_enter(Atomic.__enter__)
    Atomic.__exit__ = patch_exit(Atomic.__exit__)


def _patch_test_teardown():
    def patch_teardown(original):
        @wraps(original)
        def inner(*args, **kwargs):
            original(*args, **kwargs)
            clear_all_caches()

        inner.original = original
        return inner

    TransactionTestCase._fixture_setup = patch_teardown(
        TransactionTestCase._fixture_setup)
    TransactionTestCase._fixture_teardown = patch_teardown(
        TransactionTestCase._fixture_teardown)


def patch():
    global PATCHED
    _patch_test_teardown()
    _patch_orm_write()
    _patch_orm_read()
    _patch_atomic()
    PATCHED = True


def is_patched():
    return PATCHED
