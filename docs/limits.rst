.. _Limits:

Limits
------

High rate of database modifications
...................................

Do not use django-cachalot if your project has more than 50 database
modifications per minute on most of its tables. There will be no problem,
but django-cachalot will become inefficient and will end up slowing
your project instead of speeding it.
Read :ref:`the introduction <Introduction>` for more details.

Redis
.....

By default, Redis will not evict persistent cache keys (those with a ``None``
timeout) when the maximum memory has been reached. The cache keys created
by django-cachalot are persistent by default, so if Redis runs out of memory,
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

Memcached
.........

By default, memcached is configured for small servers.
The maximum amount of memory used by memcached is 64 MB,
and the maximum memory per cache key is 1 MB. This latter limit can lead to
weird unhandled exceptions such as
``Error: error 37 from memcached_set: SUCCESS``
if you execute queries returning more than 1 MB of data.

To increase these limits, set the ``-I`` and ``-m`` arguments when starting
memcached. If you use Ubuntu and installed the package, you can modify
`/etc/memcached.conf`, add ``-I 10m`` on a newline to set the limit
per cache key to 10 MB, and if you want increase the already existing ``-m 64``
to something like ``-m 1000`` to set the maximum cache size to 1 GB.

.. _Locmem:

Locmem
......

Locmem is a just a ``dict`` stored in a single Python process.
It’s not shared between processes, so don’t use locmem with django-cachalot
in a multi-processes project, if you use RQ or Celery for instance.

Filebased
.........

Filebased, a simple persistent cache implemented in Django, has a small bug
(`#25501 <https://code.djangoproject.com/ticket/25501>`_):
it cannot cache some objects, like psycopg2 ranges.
If you use range fields from `django.contrib.postgres` and your Django
version is affected by this bug, you need to add the tables using range fields
to :ref:`CACHALOT_UNCACHABLE_TABLES`.

.. _MySQL:

MySQL
.....

This database software already provides by default something like
django-cachalot:
`MySQL query cache <http://dev.mysql.com/doc/refman/5.7/en/query-cache.html>`_.
Unfortunately, this built-in query cache has no significant effect
since at least MySQL 5.7. However, in MySQL 5.5 it was working so well that
django-cachalot was not improving performance.
So depending on the MySQL version, django-cachalot may be useless.
See the current :ref:`django-cachalot benchmark <Benchmark>` and compare it with
`an older run of the same benchmark <http://django-cachalot.readthedocs.io/en/1.2.0/benchmark.html>`_
to see the clear difference: MySQL became 4 × slower since then!

.. _Raw SQL queries:

Raw SQL queries
...............

.. note::
   Don’t worry if you don’t understand what follow. That probably means you
   don’t use raw queries, and therefore are not directly concerned by
   those potential issues.

By default, django-cachalot tries to invalidate its cache after a raw query.
It detects if the raw query contains ``UPDATE``, ``INSERT``, ``DELETE``,
``ALTER``, ``CREATE`` or ``DROP`` and then invalidates the tables contained
in that query by comparing with models registered by Django.

This is quite robust, so if a query is not invalidated automatically
by this system, please :ref:`send a bug report <Reporting>`.
In the meantime, you can use :ref:`the API <API>` to manually invalidate
the tables where data has changed.

However, this simple system can be too efficient in some very rare cases
and lead to unwanted extra invalidations.

.. _Multiple servers:

Multiple servers clock synchronisation
......................................

Django-cachalot relies on the computer clock to handle invalidation.
If you deploy the same Django project on multiple machines,
but with a centralised cache server, all the machines serving Django need
to have their clocks as synchronised as possible.
Otherwise, invalidations will happen with a latency from one server to another.
A difference of even a few seconds can be harmful, so double check this!

To get a rough idea of the clock synchronisation of two servers, simply run
``python -c 'import time; print(time.time())'`` on both servers at the same
time. This will give you a number of seconds, and it should be almost the same,
with a difference inferior to 1 second. This number is independent
of the time zone.

To keep your clocks synchronised, use the
`Network Time Protocol <http://en.wikipedia.org/wiki/Network_Time_Protocol>`_.

Replication server
..................

If you use multiple databases where at least one is a replica of another,
django-cachalot has no way to know that the replica is modified
automatically, since it happens outside Django.
The SQL queries cached for the replica will therefore not be invalidated,
and you will see some stale queries results.

To fix this problem, you need to tell django-cachalot to also invalidate
the replica when the primary database is invalidated.
Suppose your primary database has the ``'default'`` database alias
in ``DATABASES``, and your replica has the ``'replica'`` alias.
Use :ref:`the signal <Signal>` and :meth:`cachalot.api.invalidate` this way:

.. code:: python

    from cachalot.api import invalidate
    from cachalot.signals import post_invalidation
    from django.dispatch import receiver

    @receiver(post_invalidation)
    def invalidate_replica(sender, **kwargs):
        if kwargs['db_alias'] == 'default':
            invalidate(sender, db_alias='replica')

Multiple cache servers for the same database
............................................

On large projects, we often end up having multiple Django servers on several
physical machines. For performance reasons, we generally decide to have a cache
per server, while the database stays on a single server. But the problem with
django-cachalot is that it only invalidates the cache configured using
``CACHALOT_CACHE``. So all caches end up serving stale data.

To avoid this, you need inside each Django server to be able to communicate
with the rest of the servers in order to invalidate other caches when
an invalidation occurs. If this is not possible in your situation, you must not
use django-cachalot. But if you can, each Django server must also have all
other caches in the ``CACHES`` setting. Then, you need to manually invalidate
all other caches when an invalidation occurs. Add this to a `models.py` file
of an installed application:

.. code:: python

    import threading

    from cachalot.api import invalidate
    from cachalot.signals import post_invalidation
    from django.dispatch import receiver
    from django.conf import settings

    SIGNAL_INFO = threading.local()

    @receiver(post_invalidation)
    def invalidate_other_caches(sender, **kwargs):
        if getattr(SIGNAL_INFO, 'was_called', False):
            return
        db_alias = kwargs['db_alias']
        for cache_alias in settings.CACHES:
            if cache_alias == settings.CACHALOT_CACHE:
                continue
            SIGNAL_INFO.was_called = True
            try:
                invalidate(sender, db_alias=db_alias, cache_alias=cache_alias)
            finally:
                SIGNAL_INFO.was_called = False
