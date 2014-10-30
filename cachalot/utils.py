# coding: utf-8

from __future__ import unicode_literals
from collections import defaultdict
from hashlib import md5

import django
from django.db import connections
from django.db.models.sql.where import ExtraWhere
if django.VERSION[:2] >= (1, 7):
    from django.utils.module_loading import import_string
else:
    from django.utils.module_loading import import_by_path as import_string

from .settings import cachalot_settings


def _hash_cache_key(unicode_key):
    return md5(unicode_key.encode('utf-8')).hexdigest()


def get_query_cache_key(compiler):
    sql, params = compiler.as_sql()
    return _hash_cache_key('%s:%s:%s' % (compiler.using, sql, params))


def get_table_cache_key(db_alias, table):
    return _hash_cache_key('%s:%s' % (db_alias, table))


def _get_query_cache_key(compiler):
    return import_string(cachalot_settings.CACHALOT_QUERY_KEYGEN)(compiler)


def _get_table_cache_key(db_alias, table):
    return import_string(cachalot_settings.CACHALOT_TABLE_KEYGEN)(db_alias, table)


def _get_tables(compiler):
    """
    Returns a ``set`` of all database table names used by ``query``.
    """
    query = compiler.query
    tables = set(query.tables)
    tables.add(query.model._meta.db_table)
    if query.extra_select or any(isinstance(c, ExtraWhere)
                                 for c in query.where.children):
        sql, params = compiler.as_sql()
        full_sql = sql % params
        connection = connections[compiler.using]
        for table in connection.introspection.django_table_names():
            if table in full_sql:
                tables.add(table)
    return tables


def _get_tables_cache_keys(compiler):
    using = compiler.using
    return [_get_table_cache_key(using, t) for t in _get_tables(compiler)]


def _update_tables_queries(cache, tables_cache_keys, cache_key):
    tables_queries = defaultdict(set, **cache.get_many(tables_cache_keys))
    for k in tables_cache_keys:
        tables_queries[k].add(cache_key)
    cache.set_many(tables_queries, None)


def _invalidate_tables_cache_keys(cache, tables_cache_keys):
    if hasattr(cache, 'to_be_invalidated'):
        cache.to_be_invalidated.update(tables_cache_keys)
    tables_queries = cache.get_many(tables_cache_keys)
    queries = [q for q_list in tables_queries.values() for q in q_list]
    cache.delete_many(queries + tables_cache_keys)


def _invalidate_tables(cache, compiler):
    tables_cache_keys = _get_tables_cache_keys(compiler)
    _invalidate_tables_cache_keys(cache, tables_cache_keys)
