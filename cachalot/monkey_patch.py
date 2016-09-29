# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
from functools import wraps
from time import time

from django.db.backends.utils import CursorWrapper
from django.db.models.query import EmptyResultSet
from django.db.models.signals import post_migrate
from django.db.models.sql.compiler import (
    SQLCompiler, SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler,
)
from django.db.transaction import Atomic, get_connection
from django.utils.six import binary_type

from .api import invalidate
from .cache import cachalot_caches
from .settings import cachalot_settings
from .utils import (
    _get_query_cache_key, _get_table_cache_keys, _get_tables_from_sql,
    UncachableQuery, TUPLE_OR_LIST, is_cachable, filter_cachable,
)


WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)


def _unset_raw_connection(original):
    def inner(compiler, *args, **kwargs):
        compiler.connection.raw = False
        out = original(compiler, *args, **kwargs)
        compiler.connection.raw = True
        return out
    return inner


def _get_result_or_execute_query(execute_query_func, cache,
                                 cache_key, table_cache_keys):
    data = cache.get_many(table_cache_keys + [cache_key])

    new_table_cache_keys = set(table_cache_keys)
    new_table_cache_keys.difference_update(data)

    if new_table_cache_keys:
        now = time()
        cache.set_many({k: now for k in new_table_cache_keys},
                       cachalot_settings.CACHALOT_TIMEOUT)
    elif cache_key in data:
        timestamp, result = data.pop(cache_key)
        table_times = data.values()
        if table_times and timestamp > max(table_times):
            return result

    result = execute_query_func()
    if isinstance(result, Iterable) and result.__class__ not in TUPLE_OR_LIST:
        result = list(result)

    cache.set(cache_key, (time(), result), cachalot_settings.CACHALOT_TIMEOUT)

    return result


def _patch_compiler(original):
    @wraps(original)
    @_unset_raw_connection
    def inner(compiler, *args, **kwargs):
        execute_query_func = lambda: original(compiler, *args, **kwargs)
        if not cachalot_settings.CACHALOT_ENABLED \
                or isinstance(compiler, WRITE_COMPILERS):
            return execute_query_func()

        try:
            cache_key = _get_query_cache_key(compiler)
            table_cache_keys = _get_table_cache_keys(compiler)
        except (EmptyResultSet, UncachableQuery):
            return execute_query_func()

        return _get_result_or_execute_query(
            execute_query_func,
            cachalot_caches.get_cache(db_alias=compiler.using),
            cache_key, table_cache_keys)

    return inner


def _patch_write_compiler(original):
    @wraps(original)
    @_unset_raw_connection
    def inner(write_compiler, *args, **kwargs):
        db_alias = write_compiler.using
        table = write_compiler.query.get_meta().db_table
        if is_cachable(table):
            invalidate(table, db_alias=db_alias,
                       cache_alias=cachalot_settings.CACHALOT_CACHE)
        return original(write_compiler, *args, **kwargs)

    return inner


def _patch_orm():
    SQLCompiler.execute_sql = _patch_compiler(SQLCompiler.execute_sql)
    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = _patch_write_compiler(compiler.execute_sql)


def _patch_cursor():
    def _patch_cursor_execute(original):
        @wraps(original)
        def inner(cursor, sql, *args, **kwargs):
            out = original(cursor, sql, *args, **kwargs)
            if getattr(cursor.db, 'raw', True) \
                    and cachalot_settings.CACHALOT_INVALIDATE_RAW:
                if isinstance(sql, binary_type):
                    sql = sql.decode('utf-8')
                sql = sql.lower()
                if 'update' in sql or 'insert' in sql or 'delete' in sql:
                    tables = filter_cachable(
                        set(_get_tables_from_sql(cursor.db, sql)))
                    if tables:
                        invalidate(*tables, db_alias=cursor.db.alias,
                                   cache_alias=cachalot_settings.CACHALOT_CACHE)
            return out

        return inner

    CursorWrapper.execute = _patch_cursor_execute(CursorWrapper.execute)
    CursorWrapper.executemany = _patch_cursor_execute(CursorWrapper.executemany)


def _patch_atomic():
    def patch_enter(original):
        @wraps(original)
        def inner(self):
            cachalot_caches.enter_atomic(self.using)
            original(self)

        return inner

    def patch_exit(original):
        @wraps(original)
        def inner(self, exc_type, exc_value, traceback):
            needs_rollback = get_connection(self.using).needs_rollback
            original(self, exc_type, exc_value, traceback)
            cachalot_caches.exit_atomic(
                self.using, exc_type is None and not needs_rollback)

        return inner

    Atomic.__enter__ = patch_enter(Atomic.__enter__)
    Atomic.__exit__ = patch_exit(Atomic.__exit__)


def _invalidate_on_migration(sender, **kwargs):
    invalidate(*sender.get_models(), db_alias=kwargs['using'],
               cache_alias=cachalot_settings.CACHALOT_CACHE)


def patch():
    post_migrate.connect(_invalidate_on_migration)

    _patch_cursor()
    _patch_atomic()
    _patch_orm()
