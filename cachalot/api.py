# coding: utf-8

from __future__ import unicode_literals

from django.conf import settings
from django.db import connections

from .cache import cachalot_caches
from .utils import _get_table_cache_key, _invalidate_table_cache_keys


__all__ = ('invalidate_tables', 'invalidate_models', 'invalidate_all')


def _aliases_iterator(cache_alias, db_alias):
    cache_aliases = settings.CACHES if cache_alias is None else (cache_alias,)
    db_aliases = settings.DATABASES if db_alias is None else (db_alias,)
    for cache_alias in cache_aliases:
        for db_alias in db_aliases:
            yield cache_alias, db_alias


def invalidate_tables(tables, cache_alias=None, db_alias=None):
    """
    Clears what was cached by django-cachalot implying one or more SQL tables
    from ``tables``.

    If ``cache_alias`` is specified, it only clears the SQL queries stored
    on this cache, otherwise queries from all caches are cleared.

    If ``db_alias`` is specified, it only clears the SQL queries executed
    on this database, otherwise queries from all databases are cleared.

    :arg tables: SQL tables names
    :type tables: iterable of strings
    :arg cache_alias: Alias from the Django ``CACHES`` setting
    :type cache_alias: string or NoneType
    :arg db_alias: Alias from the Django ``DATABASES`` setting
    :type db_alias: string or NoneType
    :returns: Nothing
    :rtype: NoneType
    """

    for cache_alias, db_alias in _aliases_iterator(cache_alias, db_alias):
        table_cache_keys = [_get_table_cache_key(db_alias, t) for t in tables]
        cache = cachalot_caches.get_cache(cache_alias)
        _invalidate_table_cache_keys(cache, table_cache_keys)


def invalidate_models(models, cache_alias=None, db_alias=None):
    """
    Shortcut for ``invalidate_tables`` where you can specify Django models
    instead of SQL table names.

    :arg models: Django models
    :type models: iterable of ``django.db.models.Model`` subclasses
    :arg cache_alias: Alias from the Django ``CACHES`` setting
    :type cache_alias: string or NoneType
    :arg db_alias: Alias from the Django ``DATABASES`` setting
    :type db_alias: string or NoneType
    :returns: Nothing
    :rtype: NoneType
    """

    invalidate_tables([model._meta.db_table for model in models],
                      cache_alias, db_alias)


def invalidate_all(cache_alias=None, db_alias=None):
    """
    Clears everything that was cached by django-cachalot.

    If ``cache_alias`` is specified, it only clears the SQL queries stored
    on this cache, otherwise queries from all caches are cleared.

    If ``db_alias`` is specified, it only clears the SQL queries executed
    on this database, otherwise queries from all databases are cleared.

    :arg cache_alias: Alias from the Django ``CACHES`` setting
    :type cache_alias: string or NoneType
    :arg db_alias: Alias from the Django ``DATABASES`` setting
    :type cache_alias: string or NoneType
    :returns: Nothing
    :rtype: NoneType
    """

    for cache_alias, db_alias in _aliases_iterator(cache_alias, db_alias):
        tables = connections[db_alias].introspection.table_names()
        table_cache_keys = [_get_table_cache_key(db_alias, t) for t in tables]
        _invalidate_table_cache_keys(cachalot_caches.get_cache(cache_alias),
                                     table_cache_keys)
