Django-cachalot
===============

Caches your Django ORM queries and automatically invalidates them.

**In alpha, do not use for production**

.. image:: https://raw.github.com/BertrandBordage/django-cachalot/master/django-cachalot.jpg


Quick start
-----------

Requirements
............

Django-cachalot currently requires Django 1.6
and `django-redis <https://github.com/niwibe/django-redis>`_ as your default
cache backend.  It should work with both Python 2 & 3.

Usage
.....

#. `pip install -e git+https://github.com/BertrandBordage/django-cachalot#egg=django-cachalot`
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. Enjoy!


Limits
------

Django-cachalot doesn’t cache queries it can’t reliably invalidate.
If a SQL query or a part of it is written in pure SQL, it won’t be cached.

That’s why ``QuerySet.extra`` with ``select`` or ``where`` arguments,
``Model.objects.raw(…)``, & ``cursor.execute(…)`` queries are not cached.


How django-cachalot works
-------------------------

**(If you don’t care/understand, just pretend it’s magic)**

Reverse engineering
...................

It’s a lot of Django reverse engineering combined with a strong test suite.
Such a test suite is crucial for a reverse engineering project.
If some important part of Django changes and breaks the expected behaviour,
you can be sure that the test suite will fail.

Monkey patching
...............

django-cachalot modifies Django in place during execution to add a caching tool
just before SQL queries are executed.
We detect which cache keys must be removed when some data
is created/changed/deleted on the database.


What still needs to be done
---------------------------

For version 1.0
...............

- Handle transactions
- Find out if it’s thread-safe and test it
- Write tests for `multi-table inheritance <https://docs.djangoproject.com/en/1.7/topics/db/models/#multi-table-inheritance>`_
- Add support for other caches like memcached
- Handle multiple databases
- Add invalidation on migrations in Django 1.7 (& South?)
- Add a ``CACHALOT_ENABLED`` setting
- Add a setting to choose a cache other than ``'default'``
- Use a continuous integration service to test against:

  - Python 2.7, 3.3, & 3.4
  - Django 1.6 & 1.7
  - PostgreSQL, SQLite, & MySQL
  - Redis, Memcached, LocMem

In a more distant future
........................

- Add a setting to choose if we cache ``QuerySet.order_by('?')``
- Cache ``QuerySet.extra`` if none of
  ``set(connection.introspection.table_names())
  - set(connection.introspection.django_table_name())``
  is found in the extra ``select`` and ``where`` queries
- Add a setting to disable caching on ``QuerySet.extra`` when it has ``select``
  or ``where`` rules because we can’t reliably detect other databases (and
  meta databases like ``information_schema``) on every database backend
- Maybe parse ``QuerySet.extra`` with ``select`` or ``where`` arguments
  in order to find which tables are implied, and therefore be able
  to cache them


Legacy
------

This work is highly inspired of
`johnny-cache <https://github.com/jmoiron/johnny-cache>`_, another easy-to-use
ORM caching tool!  It’s working with Django <= 1.5.
I used it in production during 3 years, it’s an excellent module!

Unfortunately, we failed to make it migrate to Django 1.6 (I was involved).
It was mostly because of the transaction system that was entirely refactored.

I also noticed a few advanced invalidation issues when using ``QuerySet.extra``
and some complex cases implying multi-table inheritance
and related ``ManyToManyField``.
