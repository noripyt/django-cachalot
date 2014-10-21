# coding: utf-8

from __future__ import unicode_literals
from collections import defaultdict
from hashlib import md5


def hash_cache_key(unicode_key):
    return md5(unicode_key.encode('utf-8')).hexdigest()


def _get_query_cache_key(compiler):
    sql, params = compiler.as_sql()
    return hash_cache_key('%s:%s:%s' % (compiler.using, sql, params))


def _get_tables(query):
    """
    Returns a ``set`` of all database table names used by ``query``.
    """
    tables = set(query.tables)
    tables.add(query.model._meta.db_table)
    return tables


def _get_table_cache_key(db_alias, table):
    return hash_cache_key('%s:%s:queries' % (db_alias, table))


def _get_tables_cache_keys(compiler):
    using = compiler.using
    return [_get_table_cache_key(using, t)
            for t in _get_tables(compiler.query)]


def _update_tables_queries(cache, compiler, cache_key):
    tables_cache_keys = _get_tables_cache_keys(compiler)
    tables_queries = defaultdict(list)
    tables_queries.update(cache.get_many(tables_cache_keys))
    for k in tables_cache_keys:
        tables_queries[k].append(cache_key)
    cache.set_many(tables_queries)


def _invalidate_tables_cache_keys(cache, tables_cache_keys):
    if hasattr(cache, 'to_be_invalidated'):
        cache.to_be_invalidated.update(tables_cache_keys)
    tables_queries = cache.get_many(tables_cache_keys)
    queries = [q for q_list in tables_queries.values() for q in q_list]
    cache.delete_many(queries + tables_cache_keys)


def _invalidate_tables(cache, compiler):
    tables_cache_keys = _get_tables_cache_keys(compiler)
    _invalidate_tables_cache_keys(cache, tables_cache_keys)
