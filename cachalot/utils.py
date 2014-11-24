# coding: utf-8

from __future__ import unicode_literals
from hashlib import md5
from time import time

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
    """
    Generates a cache key from a SQLCompiler.

    This cache key is specific to the SQL query and its context
    (which database is used).  The same query in the same context
    (= the same database) must generate the same cache key.

    :arg compiler: A SQLCompiler that will generate the SQL query
    :type compiler: django.db.models.sql.compiler.SQLCompiler
    :return: A cache key
    :rtype: str or unicode
    """
    sql, params = compiler.as_sql()
    return _hash_cache_key('%s:%s:%s' % (compiler.using, sql, params))


def get_table_cache_key(db_alias, table):
    """
    Generates a cache key from a SQL table.

    :arg db_alias: Alias of the used database
    :type db_alias: str or unicode
    :arg table: Name of the SQL table
    :type table: str or unicode
    :return: A cache key
    :rtype: str or unicode
    """
    return _hash_cache_key('%s:%s' % (db_alias, table))


def _get_query_cache_key(compiler):
    return import_string(cachalot_settings.CACHALOT_QUERY_KEYGEN)(compiler)


def _get_table_cache_key(db_alias, table):
    return import_string(cachalot_settings.CACHALOT_TABLE_KEYGEN)(db_alias, table)


def _get_tables_from_sql(connection, lowercased_sql):
    return [t for t in connection.introspection.django_table_names()
            if t in lowercased_sql]


def _get_tables(compiler):
    """
    Returns a ``set`` of all SQL table names used by ``compiler``.

    :arg compiler: A SQLCompiler that will generate the SQL query
    :type compiler: django.db.models.sql.compiler.SQLCompiler
    :return: All the SQL table names
    :rtype: set
    """
    query = compiler.query
    tables = set(query.tables)
    tables.add(query.model._meta.db_table)
    if query.extra_select or any(isinstance(c, ExtraWhere)
                                 for c in query.where.children):
        sql, params = compiler.as_sql()
        connection = connections[compiler.using]
        full_sql = (sql % params)
        tables.update(_get_tables_from_sql(connection, full_sql))
    return tables


def _get_table_cache_keys(compiler):
    using = compiler.using
    return [_get_table_cache_key(using, t) for t in _get_tables(compiler)]


def _invalidate_table_cache_keys(cache, table_cache_keys):
    if hasattr(cache, 'to_be_invalidated'):
        cache.to_be_invalidated.update(table_cache_keys)
    now = time()
    cache.set_many(dict((k, now) for k in table_cache_keys), None)


def _invalidate_tables(cache, compiler):
    table_cache_keys = _get_table_cache_keys(compiler)
    _invalidate_table_cache_keys(cache, table_cache_keys)
