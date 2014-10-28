Django-cachalot
===============

Caches your Django ORM queries and automatically invalidates them.

.. image:: https://raw.github.com/BertrandBordage/django-cachalot/master/django-cachalot.jpg

Project status:

**Currently in beta, do not use in production**

.. image:: http://img.shields.io/pypi/v/django-cachalot.svg?style=flat-square
   :target: https://pypi.python.org/pypi/django-cachalot

.. image:: http://img.shields.io/travis/BertrandBordage/django-cachalot/master.svg?style=flat-square
   :target: https://travis-ci.org/BertrandBordage/django-cachalot

.. image:: http://img.shields.io/coveralls/BertrandBordage/django-cachalot/master.svg?style=flat-square
   :target: https://coveralls.io/r/BertrandBordage/django-cachalot?branch=master

.. image:: http://img.shields.io/scrutinizer/g/BertrandBordage/django-cachalot/master.svg?style=flat-square
   :target: https://scrutinizer-ci.com/g/BertrandBordage/django-cachalot/

.. image:: http://img.shields.io/gratipay/BertrandBordage.svg?style=flat-square
   :target: https://gratipay.com/BertrandBordage/


Quick start
-----------

Requirements
............

- Django 1.6 or 1.7
- Python 2.6, 2.7, 3.2, 3.3, or 3.4
- `django-redis <https://github.com/niwibe/django-redis>`_,
  `memcached <https://docs.djangoproject.com/en/1.7/topics/cache/#memcached>`_
  (or `locmem <https://docs.djangoproject.com/en/1.7/topics/cache/#local-memory-caching>`_,
  but it’s not shared between processes, so don’t use it with RQ or Celery)
- PostgreSQL, MySQL or SQLite

Usage
.....

#. ``pip install django-cachalot``
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. Enjoy!


Settings
........

==================== ============= ============================================
Setting              Default value Description
==================== ============= ============================================
``CACHALOT_ENABLED`` ``True``      If set to ``False``, disables SQL caching
                                   but keeps invalidating to avoid stale cache
``CACHALOT_CACHE``   ``'default'`` Alias of the cache from |CACHES|_ used by
                                   django-cachalot
==================== ============= ============================================

.. |CACHES| replace:: ``CACHES``
.. _CACHES: https://docs.djangoproject.com/en/1.7/ref/settings/#std:setting-CACHES

These settings can be changed whenever you want.
You have to use ``cachalot_settings`` as a context manager, a decorator,
or simply by changing its attributes:

.. code:: python

    from cachalot.settings import cachalot_settings

    with cachalot_settings(CACHALOT_ENABLED=False):
        # SQL queries are not cached in this block

    @cachalot_settings(CACHALOT_CACHE='another_alias')
    def your_function():
        # What’s in this function uses another cache

    # Globally disables SQL caching until you set it back to True
    cachalot_settings.CACHALOT_ENABLED = False

In tests, you can use
`Django’s testing tools <https://docs.djangoproject.com/en/1.7/topics/testing/tools/#overriding-settings>`_
as well as ``cachalot_settings``.  The only difference is that you can’t use
``cachalot_settings`` to decorate a class.


Limits
------

Locmem
......

Locmem is a just a dict stored in a single Python process.
It’s not shared between processes, so don’t use locmem with django-cachalot
in a multi-processes project, if you use RQ or Celery for instance.

Raw queries
...........

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

- Add a lock around SQL query executions to avoid a stale cache issue if an
  invalidation of the same table(s) occurs concurrently
- Write tests for `multi-table inheritance <https://docs.djangoproject.com/en/1.7/topics/db/models/#multi-table-inheritance>`_

In a more distant future
........................

- Add a setting to choose if we cache ``QuerySet.order_by('?')``
- Use ``connection.introspection.table_names()`` to detect which tables
  are implied in a ``QuerySet.extra``


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
