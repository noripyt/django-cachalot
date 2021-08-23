What’s new in django-cachalot?
==============================

2.4.3
-----

- Fix annotated Now being cached (#195)
- Fix conditional annotated expressions not being cached (#196)
- Simplify annotation handling by using the flatten method (#197)
- Fix Django 3.2 default_app_config deprecation (#198)
- (Internal) Pinned psycopg2 to <2.9 due to Django 2.2 incompatibility

2.4.2
-----

- Add convenience settings `CACHALOT_ONLY_CACHABLE_APPS`
  and `CACHALOT_UNCACHABLE_APPS` (#187)
- Drop support for Django 3.0 (#189)
- (Internal) Added Django main-branch CI on cron job
- (Internal) Removed duplicate code (#190)

2.4.1
-----

- Fix Django requirement constraint to include 3.2.X not just 3.2
- (Internal) Deleted obsolete travis-matrix.py file

2.4.0
-----

- Add support for Django 3.2 (#181)
- Remove enforced system check for Django version (#175)
- Drop support for Django 2.0-2.1 and Python 3.5 (#181)
- Add support for Pymemcache for Django 3.2+ (#181)
- Reverts #157 with proper fix. (#181)
- Add ``CACHALOT_ADDITIONAL_TABLES`` setting for unmanaged models (#183)

2.3.5
-----

- Fix cachalot_disabled (#174)

2.3.4
-----

- Fix bug with externally invalidated cache keys (#120)
- Omit test files in coverage

2.3.3
-----

- Remove deprecated signal argument (#165)
- Add Python 3.9 support
- Use Discord instead since Slack doesn't save messages,
  @Andrew-Chen-Wang is not on there very much, and Discord
  has a phenomenal search functionality (with ES).

2.3.2
-----

- Cast memoryview objects to bytes to be able to pickle them (#163)

2.3.1
-----

- Added support for Django 3.1, including the new, native JSONField

2.3.0
-----

- Added context manager for temporarily disabling cachalot using `cachalot_disabled()`
- Fix for certain Subquery cases.

2.2.2
-----

- Drop support for Django 1.11 and Python 2.7
- Added fix for subqueries from Django 2.2

2.2.0
-----

- Adds Django 2.2 and 3.0 support.
- Dropped official support for Python 3.4

  - It won't run properly with Travis CI tests on MySQL.

- All Travis CI tests are fully functional.

2.1.0
-----

- Adds Django 2.1 support.

2.0.2
-----

- Adds support for ``.union``, ``.intersection`` & ``.difference``
  that should have been introduced since 1.5.0
- Fixes error raised in some rare and undetermined cases, when the cache
  backend doesn’t yield data as expected

2.0.1
-----

- Allows specifying a schema name in ``Model._meta.db_table``

2.0.0
-----

- Adds Django 2.0 support
- Drops Django 1.10 support
- Drops Django 1.8 support (1.9 support was dropped in 1.5.0)
- Adds a check to make sure it is used with a supported Django version
- Fixes a bug partially breaking django-cachalot when an error occurred during
  the end of a `transaction.atomic` block,
  typically when using deferred constraints

1.5.0
-----

- Adds Django 1.11 support
- Adds Python 3.6 support
- Drops Django 1.9 support (but 1.8 is still supported)
- Drops Python 3.3 support
- Adds ``CACHALOT_DATABASES`` to specify which databases have django-cachalot
  enabled (by default, only supported databases are enabled)
- Stops advising users to dynamically override cachalot settings as it cannot
  be thread-safe due to Django’s internals
- Invalidates tables after raw ``CREATE``, ``ALTER`` & ``DROP`` SQL queries
- Allows specifying model lookups like ``auth.User`` in the API functions
  (previously, it could only be done in the Django template tag, not in the
  Jinja2 ``get_last_invalidation`` function nor in API functions)
- Fixes the cache used by ``CachalotPanel`` if ``CACHALOT_CACHE`` is different
  from ``'default'``
- Uploads a wheel distribution of this package to PyPI starting now,
  in addition of the source release
- Improves tests

1.4.1
-----

- Fixes a circular import occurring when CachalotPanel is used
  and django-debug-toolbar is before django-cachalot in ``INSTALLED_APPS``
- Stops checking compatibility for caches other than ``CACHALOT_CACHE``

1.4.0
-----

- Fixes a bad design: ``QuerySet.select_for_update`` was cached, but it’s not
  correct since it does not lock data in the database once data was cached,
  leading to the database lock being useless in some cases
- Stops automatically invalidating other caches than ``CACHALOT_CACHE`` for
  consistency, performance, and usefulness reasons
- Fixes a minor issue: the ``post_invalidation`` signal was sent during
  transactions when calling the ``invalidate`` command
- Creates `a gitter chat room <https://gitter.im/django-cachalot/Lobby>`_
- Removes the Slack team. Slack does not allow public chat, this was therefore
  a bad idea

1.3.0
-----

- Adds Django 1.10 support
- Drops Django 1.7 support
- Drops Python 3.2 support
- Adds a Jinja2 extension with a ``cache`` statement
  and the ``get_last_invalidation`` function
- Adds a ``CACHALOT_TIMEOUT`` setting after dozens
  of private & public requests, but it’s not really useful
- Fixes a ``RuntimeError`` occurring if a ``DatabaseCache`` was used in
  a project, even if not used by django-cachalot
- Allows bytes raw queries (except on SQLite where it’s not supposed to work)
- Creates `a Slack team <https://django-cachalot.slack.com>`_ to discuss,
  easier than using Google Groups

1.2.1
-----

**Mandatory update if you’re using django-cachalot 1.2.0.**

This version reverts the cache keys hashing change from 1.2.0,
as it was leading to a non-shared cache when Python used a random seed
for hashing, which is the case by default on Python 3.3, 3.4, & 3.5,
and also on 2.7 & 3.2 if you set ``PYTHONHASHSEED=random``.

1.2.0
-----

**WARNING: This version is unsafe, it can lead to invalidation errors**

- Adds Django 1.9 support
- Simplifies and speeds up cache keys hashing
- Documents how to use django-cachalot with a replica database
- Adds ``DummyCache`` to ``VALID_CACHE_BACKENDS``
- Updates the comparison with django-cache-machine & django-cacheops by
  checking features and measuring performance instead of relying on their
  documentations and a 2-years-ago experience of them

1.1.0
-----

**Backwards incompatible changes:**

- Adds Django 1.8 support and drops Django 1.6 & Python 2.6 support
- Merges the 3 API functions ``invalidate_all``, ``invalidate_tables``,
  & ``invalidate_models`` into a single ``invalidate`` function
  while optimising it

Other additions:

- Adds a ``get_last_invalidation`` function to the API and the equivalent
  template tag
- Adds a ``CACHALOT_ONLY_CACHABLE_TABLES`` setting in order to make a whitelist
  of the only table names django-cachalot can cache
- Caches queries with IP addresses, floats, or decimals in parameters
- Adds a Django check to ensure the project uses
  compatible cache and database backends
- Adds a lot of tests, especially to test django.contrib.postgres
- Adds a comparison with django-cache-machine and django-cacheops
  in the documentation

Fixed:

- Removes a useless extra invalidation during each write operation
  to the database, leading to a small speedup
  during data modification and tests
- The ``post_invalidation`` signal was triggered during transactions
  and was not triggered when using the API or raw write queries: both issues
  are now fixed
- Fixes a very unlikely invalidation issue occurring only when an error
  occurred in a transaction after a transaction of another database nested
  in the first transaction was committed, like this:

  .. code:: python

      from django.db import transaction

      assert list(YourModel.objects.using('another_db')) == []

      try:
          with transaction.atomic():
              with transaction.atomic('another_db'):
                  obj = YourModel.objects.using('another_db').create(name='test')
              raise ZeroDivisionError
      except ZeroDivisionError:
          pass

      # Before django-cachalot 1.1.0, this assert was failing.
      assert list(YourModel.objects.using('another_db')) == [obj]


1.0.3
-----

- Fixes an invalidation issue that could rarely occur when querying on a
  ``BinaryField`` with PostgreSQL, or with some geographic queries
  (there was a small chance that a same query with different parameters
  could erroneously give the same result as the previous one)
- Adds a ``CACHALOT_UNCACHABLE_TABLES`` setting
- Fixes a Django 1.7 migrations invalidation issue in tests
  (that was leading to this error half of the time:
  ``RuntimeError: Error creating new content types. Please make sure
  contenttypes is migrated before trying to migrate apps individually.``)
- Optimises tests when using django-cachalot
  by avoid several useless cache invalidations


1.0.2
-----

- Fixes an ``AttributeError`` occurring when excluding through a many-to-many
  relation on a child model (using multi-table inheritance)
- Stops caching queries with random subqueries – for example
  ``User.objects.filter(pk__in=User.objects.order_by('?'))``
- Optimises automatic invalidation
- Adds a note about clock synchronisation


1.0.1
-----

- Fixes an invalidation issue discovered by Helen Warren that was occurring
  when updating a ``ManyToManyField`` after executing using ``.exclude``
  on that relation. For example, ``Permission.objects.all().delete()`` was not
  invalidating ``User.objects.exclude(user_permissions=None)``
- Fixes a ``UnicodeDecodeError`` introduced with python-memcached 1.54
- Adds a ``post_invalidation`` signal


1.0.0
-----

Fixes a bug occurring when caching a SQL query using a non-ascii table name.


1.0.0rc
-------

Added:

- Adds an `invalidate_cachalot` command to invalidate django-cachalot
  from a script without having to clear the whole cache
- Adds the benchmark introduction, conditions & results to the documentation
- Adds a short guide on how to configure Redis as a LRU cache

Fixed:

- Fixes a rare invalidation issue occurring when updating a many-to-many table
  after executing a queryset generating a ``HAVING`` SQL statement –
  for example,
  ``User.objects.first().user_permissions.add(Permission.objects.first())``
  was not invalidating
  ``User.objects.annotate(n=Count('user_permissions')).filter(n__gte=1)``
- Fixes an even rarer invalidation issue occurring when updating a many-to-many
  table after executing a queryset filtering nested subqueries
  by another subquery through that many-to-many table – for example::

    User.objects.filter(
        pk__in=User.objects.filter(
            pk__in=User.objects.filter(
                user_permissions__in=Permission.objects.all())))

- Avoids setting useless cache keys by using table names instead of
  Django-generated table alias


0.9.0
-----

Added:

- Caches all queries implying ``Queryset.extra``
- Invalidates raw queries
- Adds a simple API containing:
  ``invalidate_tables``, ``invalidate_models``, ``invalidate_all``
- Adds file-based cache support for Django 1.7
- Adds a setting to choose if random queries must be cached
- Adds 2 settings to customize how cache keys are generated
- Adds a django-debug-toolbar panel
- Adds a benchmark

Fixed:

- Rewrites invalidation for a better speed & memory performance
- Fixes a stale cache issue occurring when an invalidation is done
  exactly during a SQL request on the invalidated table(s)
- Fixes a stale cache issue occurring after concurrent transactions
- Uses an infinite timeout

Removed:

- Simplifies ``cachalot_settings`` and forbids its use or modification


0.8.1
-----

- Fixes an issue with pip if Django is not yet installed


0.8.0
-----

- Adds multi-database support
- Adds invalidation when altering the DB schema using `migrate`, `syncdb`,
  `flush`, `loaddata` commands (also invalidates South, if you use it)
- Small optimizations & simplifications
- Adds several tests


0.7.0
-----

- Adds thread-safety
- Optimizes the amount of cache queries during transaction

0.6.0
-----

- Adds memcached support


0.5.0
-----

- Adds ``CACHALOT_ENABLED`` & ``CACHALOT_CACHE`` settings
- Allows settings to be dynamically overridden using ``cachalot_settings``
- Adds some missing tests

0.4.1
-----

- Fixes ``pip install``.

0.4.0 (**install broken**)
--------------------------

- Adds Travis CI and adds compatibility for:

  - Django 1.6 & 1.7
  - Python 2.6, 2.7, 3.2, 3.3, & 3.4
  - locmem & Redis
  - SQLite, PostgreSQL, MySQL

0.3.0
-----

- Handles transactions
- Adds lots of tests for complex cases

0.2.0
-----

- Adds a test suite
- Fixes invalidation for data creation/deletion
- Stops caching on queries defining ``select`` or ``where`` arguments
  with ``QuerySet.extra``

0.1.0
-----

Prototype simply caching all SQL queries reading the database
and trying to invalidate them when SQL queries modify the database.

Has issues invalidating deletions and creations.
Also caches ``QuerySet.extra`` queries but can’t reliably invalidate them.
No transaction support, no test, no multi-database support, etc.
