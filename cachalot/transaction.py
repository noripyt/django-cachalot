# coding: utf-8

from __future__ import unicode_literals

from .utils import _invalidate_tables_cache_keys


class AtomicCache(dict):
    def __init__(self, parent_cache):
        super(AtomicCache, self).__init__()
        self.parent_cache = parent_cache
        self.deleted = set()
        self.to_be_invalidated = set()

    def get(self, k, default=None):
        if k in self.deleted:
            return default
        if k in self:
            return self[k]
        return self.parent_cache.get(k, default)

    def set(self, k, v):
        if k in self.deleted:
            self.deleted.remove(k)
        self[k] = v

    def get_many(self, keys):
        data = dict([(k, self[k]) for k in keys if k in self])
        missing_keys = set(keys)
        missing_keys.difference_update(self.deleted)
        missing_keys.difference_update(data)
        data.update(self.parent_cache.get_many(missing_keys))
        return data

    def set_many(self, data):
        self.deleted.difference_update(data)
        self.update(data)

    def delete_many(self, keys):
        self.deleted.update(keys)
        for k in keys:
            if k in self:
                del self[k]

    def commit(self):
        _invalidate_tables_cache_keys(self.parent_cache,
                                      list(self.to_be_invalidated))
        self.parent_cache.set_many(self)
