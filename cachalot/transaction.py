# coding: utf-8

from __future__ import unicode_literals

from .utils import _invalidate_table_cache_keys
from .settings import cachalot_settings

TIMEOUT = getattr(cachalot_settings, 'CACHALOT_TIMEOUT', None)

class AtomicCache(dict):
    def __init__(self, parent_cache):
        super(AtomicCache, self).__init__()
        self.parent_cache = parent_cache
        self.to_be_invalidated = set()

    def get(self, k, default=None):
        if k in self:
            return self[k]
        return self.parent_cache.get(k, default)

    def set(self, k, v, timeout):
        self[k] = v

    def add(self, k, v, timeout):
        if self.get(k) is None:
            self.set(k, v, timeout)

    def get_many(self, keys):
        data = dict([(k, self[k]) for k in keys if k in self])
        missing_keys = set(keys)
        missing_keys.difference_update(data)
        data.update(self.parent_cache.get_many(missing_keys))
        return data

    def set_many(self, data, timeout):
        self.update(data)

    def commit(self):
        self.parent_cache.set_many(self, TIMEOUT)
        # The previous `set_many` is not enough.  The parent cache needs to be
        # invalidated in case another transaction occurred in the meantime.
        _invalidate_table_cache_keys(self.parent_cache, self.to_be_invalidated)
