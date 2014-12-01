# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
from functools import wraps
from time import time

from django import VERSION as django_version
from django.conf import settings
if django_version >= (1, 7):
    from django.db.backends.utils import CursorWrapper
else:
    from django.db.backends.util import CursorWrapper
from django.db.models.query import EmptyResultSet
if django_version >= (1, 7):
    from django.db.models.signals import post_migrate
else:
    from django.db.models.signals import post_syncdb as post_migrate
from django.db.models.sql.compiler import (
    SQLCompiler, SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
from django.db.transaction import Atomic, get_connection
from django.test import TransactionTestCase

from .api import invalidate_all, invalidate_tables
from .cache import cachalot_caches
from .settings import cachalot_settings
from .utils import (
    _get_query_cache_key, _invalidate_tables,
    _get_table_cache_keys, _get_tables_from_sql)


WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
TIMEOUT = getattr(cachalot_settings, 'CACHALOT_TIMEOUT', None)

PATCHED = False


def is_patched():
    return PATCHED


def _unset_raw_connection(original):
    def inner(compiler, *args, **kwargs):
        compiler.connection.raw = False
        out = original(compiler, *args, **kwargs)
        compiler.connection.raw = True
        return out
    return inner


def _patch_compiler(original):
    @wraps(original)
    @_unset_raw_connection
    def inner(compiler, *args, **kwargs):
        if not cachalot_settings.CACHALOT_ENABLED \
                or isinstance(compiler, WRITE_COMPILERS) \
                or (not cachalot_settings.CACHALOT_CACHE_RANDOM
                    and '?' in compiler.query.order_by):
            return original(compiler, *args, **kwargs)

        try:
            cache_key = _get_query_cache_key(compiler)
        except EmptyResultSet:
            return original(compiler, *args, **kwargs)

        cache = cachalot_caches.get_cache()
        table_cache_keys = _get_table_cache_keys(compiler)
        data = cache.get_many(table_cache_keys + [cache_key])

        new_table_cache_keys = frozenset(table_cache_keys) - frozenset(data)

        if new_table_cache_keys:
            for table_cache_key in new_table_cache_keys:
                cache.add(table_cache_key, time(), None)
        elif cache_key in data:
            timestamp, result = data.pop(cache_key)
            if timestamp > max(data.values()):
                return result

        result = original(compiler, *args, **kwargs)
        if isinstance(result, Iterable) \
                and not isinstance(result, (tuple, list)):
            result = list(result)

        cache.set(cache_key, (time(), result), TIMEOUT)

        return result

    inner.original = original
    return inner


def _patch_write_compiler(original):
    @wraps(original)
    def inner(compiler, *args, **kwargs):
        _invalidate_tables(cachalot_caches.get_cache(), compiler)
        return original(compiler, *args, **kwargs)

    inner.original = original
    return inner


def _patch_orm():
    SQLCompiler.execute_sql = _patch_compiler(SQLCompiler.execute_sql)
    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = _patch_write_compiler(compiler.execute_sql)


def _patch_cursor():
    def _patch_cursor_execute(original):
        @wraps(original)
        def inner(cursor, sql, params=None):
            out = original(cursor, sql, params)
            if getattr(cursor.db, 'raw', True) \
                    and cachalot_settings.CACHALOT_INVALIDATE_RAW:
                full_sql = sql
                if params:
                    full_sql %= tuple(params)
                full_sql = full_sql.lower()
                if 'update' in full_sql or 'insert' in full_sql \
                        or 'delete' in full_sql:
                    tables = _get_tables_from_sql(cursor.db, full_sql)
                    invalidate_tables(tables, db_alias=cursor.db.alias)
            return out

        inner.original = original
        return inner

    CursorWrapper.execute = _patch_cursor_execute(CursorWrapper.execute)


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
            needs_rollback = get_connection(self.using).needs_rollback
            original(self, exc_type, exc_value, traceback)
            cachalot_caches.exit_atomic(exc_type is None
                                        and not needs_rollback)

        inner.original = original
        return inner

    Atomic.__enter__ = patch_enter(Atomic.__enter__)
    Atomic.__exit__ = patch_exit(Atomic.__exit__)


def _patch_tests():
    def patch_transaction_test_case(original):
        @wraps(original)
        def inner(*args, **kwargs):
            out = original(*args, **kwargs)
            invalidate_all()
            return out

        inner.original = original
        return inner

    TransactionTestCase._fixture_setup = patch_transaction_test_case(
        TransactionTestCase._fixture_setup)


def _invalidate_on_migration(sender, **kwargs):
    db_alias = kwargs['using'] if django_version >= (1, 7) else kwargs['db']
    invalidate_all(db_alias=db_alias)


def patch():
    global PATCHED

    post_migrate.connect(_invalidate_on_migration)
    if 'south' in settings.INSTALLED_APPS:
        from south.signals import post_migrate as south_post_migrate
        south_post_migrate.connect(_invalidate_on_migration)

    _patch_cursor()
    _patch_tests()
    _patch_atomic()
    _patch_orm()

    PATCHED = True
