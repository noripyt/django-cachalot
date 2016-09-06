# coding: utf-8

from __future__ import unicode_literals

from .settings import cachalot_settings


class AtomicCache(dict):
    def __init__(self, parent_cache, db_alias):
        super(AtomicCache, self).__init__()
        self.parent_cache = parent_cache
        self.db_alias = db_alias
        self.to_be_invalidated = set()

    def set(self, k, v, timeout):
        self[k] = v

    def get_many(self, keys):
        data = {k: self[k] for k in keys if k in self}
        missing_keys = set(keys)
        missing_keys.difference_update(data)
        data.update(self.parent_cache.get_many(missing_keys))
        return data

    def set_many(self, data, timeout):
        self.update(data)

    def commit(self):
        if self:
            self.parent_cache.set_many(
                self, cachalot_settings.CACHALOT_TIMEOUT)
        # The previous `set_many` is not enough.  The parent cache needs to be
        # invalidated in case another transaction occurred in the meantime.
        _invalidate_tables(self.parent_cache, self.db_alias,
                           self.to_be_invalidated)


# We import this after AtomicCache to avoid a circular import issue and
# avoid importing this locally, which degrades performance.
from .utils import _invalidate_tables
