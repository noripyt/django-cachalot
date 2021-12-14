from collections import defaultdict
from threading import local

from django.core.cache import caches
from django.db import DEFAULT_DB_ALIAS, connection

from cachalot.tenants import tenant_handler
from .settings import cachalot_settings
from .signals import post_invalidation
from .transaction import AtomicCache


class CacheHandler(local):
    @property
    def atomic_caches(self):
        if not hasattr(self, '_atomic_caches'):
            self._atomic_caches = defaultdict(list)
        return self._atomic_caches

    def get_atomic_cache(self, cache_alias, db_alias, level):
        if cache_alias not in self.atomic_caches[db_alias][level]:
            self.atomic_caches[db_alias][level][cache_alias] = AtomicCache(
                self.get_cache(cache_alias, db_alias, level-1), db_alias)
        return self.atomic_caches[db_alias][level][cache_alias]

    def get_cache(self, cache_alias=None, db_alias=None, atomic_level=-1):
        if db_alias is None:
            db_alias = DEFAULT_DB_ALIAS
        if cache_alias is None:
            cache_alias = cachalot_settings.CACHALOT_CACHE

        min_level = -len(self.atomic_caches[db_alias])
        if atomic_level < min_level:
            return caches[cache_alias]
        return self.get_atomic_cache(cache_alias, db_alias, atomic_level)

    def enter_atomic(self, db_alias):
        if db_alias is None:
            db_alias = DEFAULT_DB_ALIAS
        self.atomic_caches[db_alias].append({})

    def exit_atomic(self, db_alias, commit):
        if db_alias is None:
            db_alias = DEFAULT_DB_ALIAS
        atomic_caches = self.atomic_caches[db_alias].pop().values()
        if commit:
            to_be_invalidated = set()
            for atomic_cache in atomic_caches:
                atomic_cache.commit()
                to_be_invalidated.update(atomic_cache.to_be_invalidated)
            # This happens when committing the outermost atomic block.
            if not self.atomic_caches[db_alias]:
                for table in to_be_invalidated:
                    post_invalidation.send(table, db_alias=db_alias)


cachalot_caches = CacheHandler()


def make_key(key, key_prefix, version):
    """
    Tenant-aware function to generate a cache key.

    Constructs the key used by all other methods. Prepends the tenant
    `schema_name` and `key_prefix' in multi-tenant deployments.

    Must be configured via the KEY_FUNCTION setting.
    """
    if key in tenant_handler.public_schema_keys:
        return '%s:%s:%s:%s' % (tenant_handler.public_schema_name, key_prefix, version, key)
    return '%s:%s:%s:%s' % (connection.schema_name, key_prefix, version, key)


def reverse_key(key):
    """
    Tenant-aware function to reverse a cache key.

    Must be configured via REVERSE_KEY_FUNCTION setting for multi-tenant deployments.
    """
    return key.split(':', 3)[3]
