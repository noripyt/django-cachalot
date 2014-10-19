# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
from functools import wraps
import pickle
import re

from django.db import connection
from django.db.models.query import EmptyResultSet
from django.db.models.sql.compiler import (
    SQLCompiler, SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
    SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
from django.db.models.sql.where import ExtraWhere
from django.db.transaction import Atomic
from django.test import TransactionTestCase

from .cache import cachalot_caches
from .settings import cachalot_settings
from .utils import (
    _get_tables, _get_query_cache_key, _update_tables_queries,
    _invalidate_tables)


COMPILERS = (SQLCompiler,
             SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
             SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
READ_COMPILERS = [c for c in COMPILERS if c not in WRITE_COMPILERS]


PATCHED = False


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

            cache = cachalot_caches.get_cache()
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
            _invalidate_tables(cachalot_caches.get_cache(), compiler.query)
            return original(compiler, *args, **kwargs)

        inner.original = original
        return inner

    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = patch_execute_sql(compiler.execute_sql)


def _patch_atomic():
    def patch_enter(original):
        @wraps(original)
        def inner(self):
            cachalot_caches.enter_atomic()
            original(self)

        inner.original = original
        return inner

    def patch_exit(original):
        @wraps(original)
        def inner(self, exc_type, exc_value, traceback):
            needs_rollback = connection.needs_rollback
            original(self, exc_type, exc_value, traceback)
            cachalot_caches.exit_atomic(exc_type is None
                                        and not needs_rollback)

        inner.original = original
        return inner

    Atomic.__enter__ = patch_enter(Atomic.__enter__)
    Atomic.__exit__ = patch_exit(Atomic.__exit__)


def _patch_tests():
    def patch_before(original):
        @wraps(original)
        def inner(*args, **kwargs):
            cachalot_caches.clear_all()
            return original(*args, **kwargs)

        inner.original = original
        return inner

    def patch_after(original):
        @wraps(original)
        def inner(*args, **kwargs):
            out = original(*args, **kwargs)
            cachalot_caches.clear_all()
            return out

        inner.original = original
        return inner

    creation = connection.creation
    creation.create_test_db = patch_after(creation.create_test_db)
    creation.destroy_test_db = patch_before(creation.destroy_test_db)
    TransactionTestCase._fixture_setup = patch_after(
        TransactionTestCase._fixture_setup)
    TransactionTestCase._fixture_teardown = patch_after(
        TransactionTestCase._fixture_teardown)


def patch():
    global PATCHED
    _patch_tests()
    _patch_orm_write()
    _patch_orm_read()
    _patch_atomic()
    PATCHED = True


def is_patched():
    return PATCHED
