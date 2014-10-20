# coding: utf-8

from __future__ import unicode_literals
from threading import local

from django.conf import settings
# TODO: Replace with caches[CACHALOT_CACHE] when we drop Django 1.6 support.
from django.core.cache import get_cache as get_django_cache
from django.db import connections

from .settings import cachalot_settings
from .transaction import AtomicCache
from .utils import _get_table_cache_key, _invalidate_tables_cache_keys


class CacheHandler(local):
    @property
    def atomic_caches(self):
        if not hasattr(self, '_atomic_caches'):
            self._atomic_caches = []
        return self._atomic_caches

    def get_atomic_cache(self, cache_alias, level):
        if cache_alias not in self.atomic_caches[level]:
            self.atomic_caches[level][cache_alias] = AtomicCache(
                self.get_cache(cache_alias, level-1))
        return self.atomic_caches[level][cache_alias]

    def get_cache(self, cache_alias=None, atomic_level=-1):
        if cache_alias is None:
            cache_alias = cachalot_settings.CACHALOT_CACHE

        min_level = -len(self.atomic_caches)
        if atomic_level < min_level:
            return get_django_cache(cache_alias)
        return self.get_atomic_cache(cache_alias, atomic_level)

    def enter_atomic(self):
        self.atomic_caches.append({})

    def exit_atomic(self, commit):
        atomic_caches = self.atomic_caches.pop().values()
        if commit:
            for atomic_cache in atomic_caches:
                atomic_cache.commit()

    def clear(self, cache_alias, db_alias):
        tables = connections[db_alias].introspection.table_names()
        tables_cache_keys = [_get_table_cache_key(db_alias, t) for t in tables]

        for atomic_level in range(-(len(self.atomic_caches)+1), 0):
            cache = self.get_cache(cache_alias, atomic_level)
            _invalidate_tables_cache_keys(cache, tables_cache_keys)

    def clear_all_for_db(self, db_alias):
        for cache_alias in settings.CACHES:
            self.clear(cache_alias, db_alias)

    def clear_all(self):
        for db_alias in settings.DATABASES:
            self.clear_all_for_db(db_alias)


cachalot_caches = CacheHandler()
