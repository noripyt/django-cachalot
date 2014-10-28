What’s new in django-cachalot?
==============================

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
