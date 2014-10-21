# coding: utf-8

from __future__ import unicode_literals
from collections import Iterable
from functools import wraps
import pickle
import re

from django import VERSION as django_version
from django.conf import settings
from django.db.models.query import EmptyResultSet
if django_version >= (1, 7):
    from django.db.models.signals import post_migrate
else:
    from django.db.models.signals import post_syncdb as post_migrate
from django.db.models.sql.compiler import (
    SQLCompiler, SQLAggregateCompiler, SQLDateCompiler, SQLDateTimeCompiler,
    SQLInsertCompiler, SQLUpdateCompiler, SQLDeleteCompiler)
from django.db.models.sql.where import ExtraWhere
from django.db.transaction import Atomic, get_connection
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
                    or isinstance(compiler, WRITE_COMPILERS) \
                    or _has_extra_select_or_where(compiler.query):
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

                _update_tables_queries(cache, compiler, cache_key)

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
            _invalidate_tables(cachalot_caches.get_cache(), compiler)
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
            cachalot_caches.clear_all()
            return out

        inner.original = original
        return inner

    TransactionTestCase._fixture_setup = patch_transaction_test_case(
        TransactionTestCase._fixture_setup)


def _invalidate_on_migration(sender, **kwargs):
    db_alias = kwargs['using'] if django_version >= (1, 7) else kwargs['db']
    cachalot_caches.clear_all_for_db(db_alias)


def patch():
    global PATCHED

    post_migrate.connect(_invalidate_on_migration)
    if 'south' in settings.INSTALLED_APPS:
        from south.signals import post_migrate as south_post_migrate
        south_post_migrate.connect(_invalidate_on_migration)

    _patch_tests()
    _patch_atomic()
    _patch_orm_write()
    _patch_orm_read()

    PATCHED = True


def is_patched():
    return PATCHED
