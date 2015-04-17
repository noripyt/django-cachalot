Quick start
-----------

Requirements
............

- Django 1.6 or 1.7
- Python 2.6, 2.7, 3.2, 3.3, or 3.4
- a cache configured as ``'default'`` with one of these backends:

  - `django-redis <https://github.com/niwibe/django-redis>`_
  - `memcached <https://docs.djangoproject.com/en/1.7/topics/cache/#memcached>`_
    (using either python-memcached or pylibmc (but pylibmc is only supported
    with Django >= 1.7))
  - `filebased <https://docs.djangoproject.com/en/1.7/topics/cache/#filesystem-caching>`_
    (only with Django >= 1.7 as it was not thread-safe before)
  - `locmem <https://docs.djangoproject.com/en/1.7/topics/cache/#local-memory-caching>`_
    (but it’s not shared between processes, see :ref:`Limits`)

- one of these databases:

  - PostgreSQL
  - SQLite
  - MySQL (but you probably don’t need django-cachalot in this case,
    see :ref:`Limits`)

Usage
.....

#. ``pip install django-cachalot``
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. Be aware of :ref:`the few limits <limits>`
#. If you use
   `django-debug-toolbar <https://github.com/django-debug-toolbar/django-debug-toolbar>`_,
   you can add ``'cachalot.panels.CachalotPanel',``
   to your ``DEBUG_TOOLBAR_PANELS``
#. If you need to invalidate all django-cachalot cache keys from an external script
   – typically after restoring a SQL database –, simply run
   ``./manage.py invalidate_cachalot``
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

Django-cachalot is built so that its settings can be dynamically changed.
For example:

.. code:: python

    from django.conf import settings
    from django.test.utils import override_settings

    with override_settings(CACHALOT_ENABLED=False):
        # SQL queries are not cached in this block

    @override_settings(CACHALOT_CACHE='another_alias')
    def your_function():
        # What’s in this function uses another cache

    # Globally disables SQL caching until you set it back to True
    settings.CACHALOT_ENABLED = False


Signal
......

``cachalot.signals.post_invalidation`` is available if you need to do something
just after a cache invalidation (when you modify something in a SQL table).
``sender`` is the name of the SQL table invalidated, and a keyword argument
``db_alias`` explains which database is affected by the invalidation.
Be careful when you specify ``sender``, as it is sensible to string type.
To be sure, use ``Model._meta.db_table``.

Example:

.. code:: python

    from cachalot.signals import post_invalidation
    from django.dispatch import receiver
    from django.core.mail import mail_admins
    from django.contrib.auth import *

    # This prints a message to the console after each table invalidation
    def invalidation_debug(sender, **kwargs):
        db_alias = kwargs['db_alias']
        print('%s was invalidated in the DB configured as %s'
              % (sender, db_alias))

    post_invalidation.connect(invalidation_debug)

    # Using the `receiver` decorator is just a nicer way
    # to write the same thing as `signal.connect`.
    # Here we specify `sender` so that the function is executed only if
    # the table invalidated is the one specified.
    # We also connect it several times to be executed for several senders.
    @receiver(post_invalidation, sender=User.groups.through._meta.db_table)
    @receiver(post_invalidation, sender=User.user_permissions.through._meta.db_table)
    @receiver(post_invalidation, sender=Group.permissions.through._meta.db_table)
    def warn_admin(sender, **kwargs):
        mail_admins('User permissions changed',
                    'Someone probably gained or lost Django permissions.')
