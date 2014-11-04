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
#. Be aware of :ref:`the few limits <limits>`
#. Enjoy!


Settings
........

``CACHALOT_ENABLED``
~~~~~~~~~~~~~~~~~~~~

:Default: ``True``
:Description: If set to ``False``, disables SQL caching but keeps invalidating
              to avoid stale cache

``CACHALOT_CACHE``
~~~~~~~~~~~~~~~~~~

:Default: ``'default'``
:Description: Alias of the cache from |CACHES|_ used by django-cachalot

.. |CACHES| replace:: ``CACHES``
.. _CACHES: https://docs.djangoproject.com/en/1.7/ref/settings/#std:setting-CACHES

``CACHALOT_CACHE_RANDOM``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``False``
:Description: If set to ``True``, caches random queries
              (those with ``order_by('?')``)

.. _CACHALOT_INVALIDATE_RAW:

``CACHALOT_INVALIDATE_RAW``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``True``
:Description: If set to ``False``, disables automatic invalidation on raw
              SQL queries – read :ref:`Raw queries limits` for more info

``CACHALOT_QUERY_KEYGEN``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``'cachalot.utils.get_query_cache_key'``
:Description: Python module path to the function that will be used to generate
              the cache key of a SQL query

``CACHALOT_TABLE_KEYGEN``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``'cachalot.utils.get_table_cache_key'``
:Description: Python module path to the function that will be used to generate
              the cache key of a SQL table

.. _Dynamic overriding:

Dynamic overriding
~~~~~~~~~~~~~~~~~~

Obviously, you can set these settings in your Django settings.
But you can also change them whenever you want!
Simply use ``cachalot_settings`` as a context manager, a decorator,
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
