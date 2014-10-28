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
