.. _limits:

Limits
------

Locmem
......

Locmem is a just a ``dict`` stored in a single Python process.
It’s not shared between processes, so don’t use locmem with django-cachalot
in a multi-processes project, if you use RQ or Celery for instance.

Redis
.....

By default, Redis will not evict persistent cache keys (those with a ``None``
timeout) when the maximum memory has been reached. The cache keys created
by django-cachalot are persistent, so if Redis runs out of memory,
django-cachalot and all other ``cache.set`` will raise
``ResponseError: OOM command not allowed when used memory > 'maxmemory'.``
because Redis is not allowed to delete persistent keys.

To avoid this, 2 solutions:

- If you only store disposable data in Redis, you can change
  ``maxmemory-policy`` to ``allkeys-lru`` in your Redis configuration.
  Be aware that this setting is global; all your Redis databases will use it.
  **If you don’t know what you’re doing, use the next solution or use
  another cache backend.**
- Increase ``maxmemory`` in your Redis configuration.
  You can start by setting it to a high value (for example half of your RAM)
  then decrease it by looking at the Redis database maximum size using
  ``redis-cli info memory``.

For more information, read
`Using Redis as a LRU cache <http://redis.io/topics/lru-cache>`_.

MySQL
.....

This database software already provides by default something like
django-cachalot:
`MySQL query cache <http://dev.mysql.com/doc/refman/5.7/en/query-cache.html>`_.
Django-cachalot will slow down your queries if that query cache is enabled.
If it’s not enabled, django-cachalot will make queries much faster.
But you should probably better enable the query cache instead.

.. _Raw queries limits:

Raw SQL queries
...............

.. note::
   Don’t worry if you don’t understand what follow. That probably means you
   don’t use raw queries, and therefore are not directly concerned by
   those potential issues.

By default, django-cachalot tries to invalidate its cache after a raw query.
It detects if the raw query contains ``UPDATE``, ``INSERT`` or ``DELETE``,
and then invalidates the tables contained in that query by comparing
with models registered by Django.

This is quite robust, so if a query is not invalidated automatically
by this system, please :ref:`send a bug report <reporting>`.
In the meantime, you can use :ref:`the API <API>` to manually invalidate
the tables where data has changed.

However, this simple system can be too efficient in some cases and lead to
unwanted extra invalidations.
In such cases, you may want to partially disable this behaviour by
:ref:`dynamically overriding settings <Dynamic overriding>` to set
:ref:`CACHALOT_INVALIDATE_RAW` to ``False``.
After that, use :ref:`the API <API>` to manually invalidate the tables
you modified.
