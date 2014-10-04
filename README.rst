Django-cachalot
===============

Caches your Django ORM queries and automatically invalidates them.

.. image:: https://raw.github.com/BertrandBordage/django-cachalot/master/django-cachalot.jpg

Project status:

**Currently in beta, do not use in production**

.. image:: https://travis-ci.org/BertrandBordage/django-cachalot.png
   :target: https://travis-ci.org/BertrandBordage/django-cachalot

.. image:: https://coveralls.io/repos/BertrandBordage/django-cachalot/badge.png?branch=master
   :target: https://coveralls.io/r/BertrandBordage/django-cachalot?branch=master


Quick start
-----------

Requirements
............

- Django 1.6 or 1.7
- Python 2.6, 2.7, 3.2, 3.3, or 3.4
- `locmem <https://docs.djangoproject.com/en/1.7/topics/cache/#local-memory-caching>`_
  or `django-redis <https://github.com/niwibe/django-redis>`_
  (memcached coming soon)
- SQLite, PostgreSQL or MySQL (it should work with Oracle,
  but I don’t have 17.5k$ to test)

Usage
.....

#. ``pip install django-cachalot``
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. Enjoy!


Settings
........

================== ============= ==============================================
Setting            Default value Description
================== ============= ==============================================
``CACHALOT_CACHE`` ``'default'`` Name of the cache from |CACHES|_ used by
                                 django-cachalot
================== ============= ==============================================


.. |CACHES| replace:: ``CACHES``
.. _CACHES: https://docs.djangoproject.com/en/1.7/ref/settings/#std:setting-CACHES


Limits
------

Django-cachalot doesn’t cache queries it can’t reliably invalidate.
If a SQL query or a part of it is written in pure SQL, it won’t be cached.

That’s why ``QuerySet.extra`` with ``select`` or ``where`` arguments,
``Model.objects.raw(…)``, & ``cursor.execute(…)`` queries are not cached.


Bug reports, questions, discussion, new features
------------------------------------------------

- If you spotted **a bug**, please file a precise bug report
  `on GitHub <https://github.com/BertrandBordage/django-cachalot/issues>`_
- If you have **a question** on how django-cachalot works or to **simply
  discuss**, `go to our Google group
  <https://groups.google.com/forum/#!forum/django-cachalot>`_.
- If you want **to add a feature**:

  - if you have an idea on how to implement it, you can fork the project
    and send a pull request, but **please open an issue first**, because
    someone else could already be working on it
  - if you’re sure that it’s a must-have feature, open an issue
  - if it’s just a vague idea, please ask on google groups before


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

- Find out if it’s thread-safe and test it
- Write tests for `multi-table inheritance <https://docs.djangoproject.com/en/1.7/topics/db/models/#multi-table-inheritance>`_
- Add memcached support
- Handle multiple databases
- Add invalidation on migrations in Django 1.7 (& South?)
- Add a ``CACHALOT_ENABLED`` setting

In a more distant future
........................

- Add a setting to choose if we cache ``QuerySet.order_by('?')``
- Cache ``QuerySet.extra`` if none of
  ``set(connection.introspection.table_names())
  - set(connection.introspection.django_table_names())``
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
