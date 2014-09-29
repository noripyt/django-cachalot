What’s new in django-cachalot?
==============================

0.4
---

- Adds Travis CI and adds compatibility for:

  - Django 1.6 & 1.7
  - Python 2.6, 2.7, 3.2, 3.3, & 3.4
  - locmem & Redis
  - SQLite, PostgreSQL, MySQL

0.3
---

- Handles transactions
- Adds lots of tests for complex cases

0.2
---

- Adds a test suite
- Fixes invalidation for data creation/deletion
- Stops caching on queries defining ``select`` or ``where`` arguments
  with ``QuerySet.extra``

0.1
---

Prototype simply caching all SQL queries reading the database
and trying to invalidate them when SQL queries modify the database.

Has issues invalidating deletions and creations.
Also caches ``QuerySet.extra`` queries but can’t reliably invalidate them.
No transaction support, no test, no multi-database support, etc.
