# coding: utf-8

from __future__ import unicode_literals

from .utils import _invalidate_tables_cache_keys


class AtomicCache(dict):
    def __init__(self, parent_cache):
        super(AtomicCache, self).__init__()
        self.parent_cache = parent_cache
        self.to_be_deleted = set()
        self.to_be_invalidated = set()

    def get(self, k, default=None):
        if k in self.to_be_deleted:
            return default
        if k in self:
            return self[k]
        return self.parent_cache.get(k, default)

    def set(self, k, v):
        if k in self.to_be_deleted:
            self.to_be_deleted.remove(k)
        self[k] = v

    def delete(self, k):
        self.to_be_deleted.add(k)

    def get_many(self, keys):
        data = dict([(k, self[k]) for k in keys if
                     k in self and k not in self.to_be_deleted])
        missing_keys = set(keys)
        missing_keys.difference_update(data)
        data.update(self.parent_cache.get_many(missing_keys))
        return data

    def set_many(self, data):
        self.to_be_deleted.difference_update(data)
        self.update(data)

    def delete_many(self, keys):
        self.to_be_deleted.update(keys)

    def commit(self):
        _invalidate_tables_cache_keys(self.parent_cache,
                                      list(self.to_be_invalidated))
        self.parent_cache.set_many(self)
        self.parent_cache.delete_many(self.to_be_deleted)
