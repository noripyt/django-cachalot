# coding: utf-8

from __future__ import unicode_literals

from .utils import _invalidate_table_cache_keys


class AtomicCache(dict):
    def __init__(self, parent_cache):
        super(AtomicCache, self).__init__()
        self.parent_cache = parent_cache
        self.to_be_invalidated = set()

    def set(self, k, v, timeout):
        self[k] = v

    def get_many(self, keys):
        data = {}
        for k in keys:
            if k in self:
                data[k] = self[k]
        missing_keys = set(keys)
        missing_keys.difference_update(data)
        data.update(self.parent_cache.get_many(missing_keys))
        return data

    def set_many(self, data, timeout):
        self.update(data)

    def commit(self):
        self.parent_cache.set_many(self, None)
        # The previous `set_many` is not enough.  The parent cache needs to be
        # invalidated in case another transaction occurred in the meantime.
        _invalidate_table_cache_keys(self.parent_cache, self.to_be_invalidated)
