# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
from time import time

from django.db.backends.utils import CursorWrapper
from django.db.models.query import EmptyResultSet
from django.db.models.signals import post_migrate
from django.db.models.sql.compiler import (
    SQLCompiler, SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler,
)
from django.db.transaction import Atomic, get_connection
from django.utils.six import binary_type, wraps, PY3

if PY3:
    from threading import get_ident
else:
    from thread import get_ident

from .api import invalidate
from .cache import cachalot_caches
from .settings import cachalot_settings, ITERABLES
from .utils import (
    _get_table_cache_keys, _get_tables_from_sql,
    UncachableQuery, is_cachable, filter_cachable,
)


class Disabled:
    """
        The purpose of this class is to provide a way for long running
        transactions like a data import which mostly inserts and updates data
        to disable cachalot.

        While the disabled transaction is running other transactions will still
        use the cache and it will invalidate when being disabled is turned off.

        A clear function exists in case it is ever needed.

        Example 1:
            from cachalot.monkey_patch import DISABLE_CACHING

            with DISABLE_CACHING:
                DISABLE_CACHING.do_not_invalidate()  # Optional Line, will not invalidate after the with

                # Optional line that allows you to change the cache and db aliases used when invalidating.
                DISABLE_CACHING.set_aliases(cache_alias='default', db_alias='default')

                # Code to run while the cache is disabled


        Example 2:
            from cachalot.monkey_patch import DISABLE_CACHING

            try:
                DISABLE_CACHING.enable()
                # Code to run while the cache is disabled

            finally:
                # invalidate_cache is only needed if you do not want to invalidate the cache.
                # Also allow you to change the cache and db aliases used when invalidating.
                DISABLE_CACHING.disable(invalidate_cache=False, cache_alias='default', db_alias='default')
    """
    def __init__(self):
        self.threads = frozenset()
        self.invalidate_on_exit = {}
        self.has_disabled_threads = False

    def __enter__(self, invalidate_on_exit=True):
        thread_ident = get_ident()
        thread_data = set(self.threads)
        thread_data.add(thread_ident)
        self.threads = frozenset(thread_data)
        self.invalidate_on_exit[thread_ident] = {
            'cache_alias': 'default',
            'db_alias': 'default'
        }
        self.has_disabled_threads = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        thread_ident = get_ident()
        if thread_ident in self.threads:
            thread_data = set(self.threads)
            thread_data.remove(thread_ident)
            self.threads = frozenset(thread_data)
            if not self.threads:
                self.has_disabled_threads = False
            if thread_ident in self.invalidate_on_exit:
                aliases = self.invalidate_on_exit.pop(thread_ident)
                invalidate(*[], cache_alias=aliases['cache_alias'], db_alias=aliases['db_alias'])

    def set_aliases(self, cache_alias='default', db_alias='default'):
        thread_ident = get_ident()
        if thread_ident in self.invalidate_on_exit:
            self.invalidate_on_exit[thread_ident] = {
                'cache_alias': cache_alias,
                'db_alias': db_alias
            }

    def do_not_invalidate(self):
        thread_ident = get_ident()
        if thread_ident in self.invalidate_on_exit:
            self.invalidate_on_exit.pop(thread_ident)

    def get(self):
        return self.has_disabled_threads and get_ident() in self.threads

    def enable(self):
        thread_data = set(self.threads)
        thread_data.add(get_ident())
        self.threads = frozenset(thread_data)
        self.has_disabled_threads = True

    def disable(self, invalidate_cache=True, cache_alias='default', db_alias='default'):
        thread_ident = get_ident()
        if thread_ident in self.threads:
            thread_data = set(self.threads)
            thread_data.remove(thread_ident)
            self.threads = frozenset(thread_data)
            if not self.threads:
                self.has_disabled_threads = False
            if invalidate_cache:
                invalidate(*[], cache_alias=cache_alias, db_alias=db_alias)

    def clear(self):
        self.threads = frozenset()
        self.invalidate_on_exit = {}
        self.has_disabled_threads = False


DISABLE_CACHING = Disabled()

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

    if not new_table_cache_keys and cache_key in data:
        timestamp, result = data.pop(cache_key)
        if timestamp >= max(data.values()):
            return result

    result = execute_query_func()
    if result.__class__ not in ITERABLES and isinstance(result, Iterable):
        result = list(result)

    now = time()
    to_be_set = {k: now for k in new_table_cache_keys}
    to_be_set[cache_key] = (now, result)
    cache.set_many(to_be_set, cachalot_settings.CACHALOT_TIMEOUT)

    return result


def _patch_compiler(original):
    @wraps(original)
    @_unset_raw_connection
    def inner(compiler, *args, **kwargs):
        if DISABLE_CACHING.get():
            return original(compiler, *args, **kwargs)

        execute_query_func = lambda: original(compiler, *args, **kwargs)
        db_alias = compiler.using
        if db_alias not in cachalot_settings.CACHALOT_DATABASES \
                or isinstance(compiler, WRITE_COMPILERS):
            return execute_query_func()

        try:
            cache_key = cachalot_settings.CACHALOT_QUERY_KEYGEN(compiler)
            table_cache_keys = _get_table_cache_keys(compiler)
        except (EmptyResultSet, UncachableQuery):
            return execute_query_func()

        return _get_result_or_execute_query(
            execute_query_func,
            cachalot_caches.get_cache(db_alias=db_alias),
            cache_key, table_cache_keys)

    return inner


def _patch_write_compiler(original):
    @wraps(original)
    @_unset_raw_connection
    def inner(write_compiler, *args, **kwargs):
        if DISABLE_CACHING.get():
            return original(write_compiler, *args, **kwargs)

        db_alias = write_compiler.using
        table = write_compiler.query.get_meta().db_table
        if is_cachable(table):
            invalidate(table, db_alias=db_alias,
                       cache_alias=cachalot_settings.CACHALOT_CACHE)
        return original(write_compiler, *args, **kwargs)

    return inner


def _patch_orm():
    if cachalot_settings.CACHALOT_ENABLED:
        SQLCompiler.execute_sql = _patch_compiler(SQLCompiler.execute_sql)
    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = _patch_write_compiler(compiler.execute_sql)


def _unpatch_orm():
    if hasattr(SQLCompiler.execute_sql, '__wrapped__'):
        SQLCompiler.execute_sql = SQLCompiler.execute_sql.__wrapped__
    for compiler in WRITE_COMPILERS:
        compiler.execute_sql = compiler.execute_sql.__wrapped__


def _patch_cursor():
    def _patch_cursor_execute(original):
        @wraps(original)
        def inner(cursor, sql, *args, **kwargs):
            if DISABLE_CACHING.get():
                return original(cursor, sql, *args, **kwargs)

            out = original(cursor, sql, *args, **kwargs)
            connection = cursor.db
            if getattr(connection, 'raw', True):
                if isinstance(sql, binary_type):
                    sql = sql.decode('utf-8')
                sql = sql.lower()
                if 'update' in sql or 'insert' in sql or 'delete' in sql \
                        or 'alter' in sql or 'create' in sql or 'drop' in sql:
                    tables = filter_cachable(
                        _get_tables_from_sql(connection, sql))
                    if tables:
                        invalidate(*tables, db_alias=connection.alias,
                                   cache_alias=cachalot_settings.CACHALOT_CACHE)
            return out

        return inner

    if cachalot_settings.CACHALOT_INVALIDATE_RAW:
        CursorWrapper.execute = _patch_cursor_execute(CursorWrapper.execute)
        CursorWrapper.executemany = \
            _patch_cursor_execute(CursorWrapper.executemany)


def _unpatch_cursor():
    if hasattr(CursorWrapper.execute, '__wrapped__'):
        CursorWrapper.execute = CursorWrapper.execute.__wrapped__
        CursorWrapper.executemany = CursorWrapper.executemany.__wrapped__


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


def _unpatch_atomic():
    Atomic.__enter__ = Atomic.__enter__.__wrapped__
    Atomic.__exit__ = Atomic.__exit__.__wrapped__


def _invalidate_on_migration(sender, **kwargs):
    invalidate(*sender.get_models(), db_alias=kwargs['using'],
               cache_alias=cachalot_settings.CACHALOT_CACHE)


def patch():
    post_migrate.connect(_invalidate_on_migration)

    _patch_cursor()
    _patch_atomic()
    _patch_orm()


def unpatch():
    post_migrate.disconnect(_invalidate_on_migration)

    _unpatch_cursor()
    _unpatch_atomic()
    _unpatch_orm()
