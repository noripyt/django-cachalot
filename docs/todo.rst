What still needs to be done
---------------------------

- Cache raw queries
- Test multi-location caches if possible
- Allow setting `CACHALOT_CACHE` to `None` in order to disable django-cachalot
  persistence. SQL queries would only be cached during transactions, so setting
  `ATOMIC_REQUESTS` to `True` would cache SQL queries only during
  a request-response cycle. This would be useful for websites with a lot of
  invalidations (social network for example), but with several times the same
  SQL queries in a single response-request cycle, as it occurs in Django admin.
