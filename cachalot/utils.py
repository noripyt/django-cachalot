# coding: utf-8

from __future__ import unicode_literals
from hashlib import md5


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
    if hasattr(cache, 'to_be_invalidated'):
        cache.to_be_invalidated.update(tables_cache_keys)
    tables_queries = cache.get_many(tables_cache_keys)
    queries = [q for k in tables_cache_keys for q in tables_queries.get(k, [])]
    cache.delete_many(queries + tables_cache_keys)


def _invalidate_tables(cache, query):
    tables_cache_keys = _get_tables_cache_keys(query)
    _invalidate_tables_cache_keys(cache, tables_cache_keys)
