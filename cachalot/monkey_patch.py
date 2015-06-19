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

from .api import invalidate_all, invalidate_tables, invalidate_models
from .cache import cachalot_caches
from .settings import cachalot_settings
from .utils import (
    _get_query_cache_key, _invalidate_table,
    _get_table_cache_keys, _get_tables_from_sql, UncachableQuery)


WRITE_COMPILERS = (SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)


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


TUPLE_OR_LIST = (tuple, list)


def _get_result_or_execute_query(execute_query_func, cache_key,
                                 table_cache_keys):
    cache = cachalot_caches.get_cache()
    data = cache.get_many(table_cache_keys + [cache_key])

    new_table_cache_keys = set(table_cache_keys)
    new_table_cache_keys.difference_update(data)

    if new_table_cache_keys:
        now = time()
        d = {}
        for k in new_table_cache_keys:
            d[k] = now
        cache.set_many(d, None)
    elif cache_key in data:
        timestamp, result = data.pop(cache_key)
        table_times = data.values()
        if table_times and timestamp > max(table_times):
            return result

    result = execute_query_func()
    if isinstance(result, Iterable) and result.__class__ not in TUPLE_OR_LIST:
        result = list(result)

    cache.set(cache_key, (time(), result), None)

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
            execute_query_func, cache_key, table_cache_keys)

    return inner


def _patch_write_compiler(original):
    @wraps(original)
    def inner(write_compiler, *args, **kwargs):
        _invalidate_table(cachalot_caches.get_cache(), write_compiler)
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
                sql = sql.lower()
                if 'update' in sql or 'insert' in sql or 'delete' in sql:
                    tables = _get_tables_from_sql(cursor.db, sql)
                    invalidate_tables(tables, db_alias=cursor.db.alias)
            return out

        return inner

    CursorWrapper.execute = _patch_cursor_execute(CursorWrapper.execute)
    CursorWrapper.executemany = _patch_cursor_execute(CursorWrapper.executemany)


def _patch_atomic():
    def patch_enter(original):
        @wraps(original)
        def inner(self):
            cachalot_caches.enter_atomic()
            original(self)

        return inner

    def patch_exit(original):
        @wraps(original)
        def inner(self, exc_type, exc_value, traceback):
            needs_rollback = get_connection(self.using).needs_rollback
            original(self, exc_type, exc_value, traceback)
            cachalot_caches.exit_atomic(exc_type is None
                                        and not needs_rollback)

        return inner

    Atomic.__enter__ = patch_enter(Atomic.__enter__)
    Atomic.__exit__ = patch_exit(Atomic.__exit__)

if django_version >= (1, 7):
    def _invalidate_on_migration(sender, **kwargs):
        invalidate_models(sender.get_models(), db_alias=kwargs['using'])
else:
    def _invalidate_on_migration(sender, **kwargs):
        invalidate_all(db_alias=kwargs['db'])


def patch():
    global PATCHED

    post_migrate.connect(_invalidate_on_migration)
    if 'south' in settings.INSTALLED_APPS:
        from south.signals import post_migrate as south_post_migrate
        south_post_migrate.connect(_invalidate_on_migration)

    _patch_cursor()
    _patch_atomic()
    _patch_orm()

    PATCHED = True
