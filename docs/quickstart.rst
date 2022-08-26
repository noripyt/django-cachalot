Quick start
-----------

Requirements
............

- Django 2.2, 3.2, 4.0-4.1
- Python 3.7-3.10
- a cache configured as ``'default'`` with one of these backends:

  - `django-redis <https://github.com/niwinz/django-redis>`_
  - `memcached <https://docs.djangoproject.com/en/dev/topics/cache/#memcached>`_
    (using either python-memcached or pylibmc)
  - `filebased <https://docs.djangoproject.com/en/dev/topics/cache/#filesystem-caching>`_
  - `locmem <https://docs.djangoproject.com/en/dev/topics/cache/#local-memory-caching>`_
    (but it’s not shared between processes, see :ref:`locmem limits <Locmem>`)

- one of these databases:

  - PostgreSQL
  - SQLite
  - MySQL (but on older versions like MySQL 5.5, django-cachalot has no effect,
    see :ref:`MySQL limits <MySQL>`)

Usage
.....

#. ``pip install django-cachalot``
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. If you use multiple servers with a common cache server,
   :ref:`double check their clock synchronisation <multiple servers>`
#. If you modify data outside Django
   – typically after restoring a SQL database –,
   use the :ref:`manage.py command <Command>`
#. Be aware of :ref:`the few other limits <Limits>`
#. If you use
   `django-debug-toolbar <https://github.com/jazzband/django-debug-toolbar>`_,
   you can add ``'cachalot.panels.CachalotPanel',``
   to your ``DEBUG_TOOLBAR_PANELS``
#. Enjoy!


.. _Settings:

Settings
........

``CACHALOT_ENABLED``
~~~~~~~~~~~~~~~~~~~~

:Default: ``True``
:Description: If set to ``False``, disables SQL caching but keeps invalidating
              to avoid stale cache.

``CACHALOT_CACHE``
~~~~~~~~~~~~~~~~~~

:Default: ``'default'``
:Description:
  Alias of the cache from |CACHES|_ used by django-cachalot.

  .. warning::
     After modifying this setting, you should invalidate the cache
     :ref:`using the manage.py command <Command>` or :ref:`the API <API>`.
     Indeed, only the cache configured using this setting is automatically
     invalidated by django-cachalot – for optimisation reasons. So when you
     change this setting, you end up on a cache that may contain stale data.

.. |CACHES| replace:: ``CACHES``
.. _CACHES: https://docs.djangoproject.com/en/dev/ref/settings/#caches

``CACHALOT_DATABASES``
~~~~~~~~~~~~~~~~~~~~~~

:Default: ``'supported_only'``
:Description:
  List, tuple, set or frozenset of database aliases from |DATABASES|_ against
  which django-cachalot will do caching. By default, the special value
  ``'supported_only'`` enables django-cachalot only on supported database
  engines.

.. |DATABASES| replace:: ``DATABASES``
.. _DATABASES: https://docs.djangoproject.com/en/dev/ref/settings/#databases

``CACHALOT_TIMEOUT``
~~~~~~~~~~~~~~~~~~~~

:Default: ``None``
:Description:
  Number of seconds during which the cache should consider data as valid.
  ``None`` means an infinite timeout.

  .. warning::
     Cache timeouts don’t work in a strict way on most cache backends.
     A cache might not keep data during the requested timeout:
     it can keep it in memory during a shorter time than the specified timeout.
     It can even keep it longer, even if data is not returned when you request it.
     So **don’t rely on timeouts to limit the size of your database**,
     you might face some unexpected behaviour.
     Always set the maximum cache size instead.

``CACHALOT_CACHE_RANDOM``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``False``
:Description: If set to ``True``, caches random queries
              (those with ``order_by('?')``).

.. _CACHALOT_INVALIDATE_RAW:

``CACHALOT_INVALIDATE_RAW``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``True``
:Description:
  If set to ``False``, disables automatic invalidation on raw
  SQL queries – read :ref:`raw queries limits <Raw SQL queries>` for more info.


.. _CACHALOT_ONLY_CACHABLE_TABLES:

``CACHALOT_ONLY_CACHABLE_TABLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``frozenset()``
:Description:
  Sequence of SQL table names that will be the only ones django-cachalot
  will cache. Only queries with a subset of these tables will be cached.
  The sequence being empty (as it is by default) does not mean that no table
  can be cached: it disables this setting, so any table can be cached.
  :ref:`CACHALOT_UNCACHABLE_TABLES` has more weight than this:
  if you add a table to both settings, it will never be cached.
  Run ``./manage.py invalidate_cachalot`` after changing this setting.

``CACHALOT_ONLY_CACHABLE_APPS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``frozenset()``
:Description:
  Sequence of Django apps whose associated models will be appended to
  :ref:`CACHALOT_ONLY_CACHABLE_TABLES`. The rules between
  :ref:`CACHALOT_UNCACHABLE_TABLES` and :ref:`CACHALOT_ONLY_CACHABLE_TABLES` still
  apply as this setting only appends the given Django apps' tables on initial
  Django setup.


.. _CACHALOT_UNCACHABLE_TABLES:

``CACHALOT_UNCACHABLE_TABLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``frozenset(('django_migrations',))``
:Description:
  Sequence of SQL table names that will be ignored by django-cachalot.
  Queries using a table mentioned in this setting will not be cached.
  Always keep ``'django_migrations'`` in it, otherwise you may face
  some issues, especially during tests.
  Run ``./manage.py invalidate_cachalot`` after changing this setting.

``CACHALOT_UNCACHABLE_APPS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``frozenset()``
:Description:
  Sequence of Django apps whose associated models will be appended to
  :ref:`CACHALOT_UNCACHABLE_TABLES`. The rules between
  :ref:`CACHALOT_UNCACHABLE_TABLES` and :ref:`CACHALOT_ONLY_CACHABLE_TABLES` still
  apply as this setting only appends the given Django apps' tables on initial
  Django setup.

``CACHALOT_ADDITIONAL_TABLES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``list()``
:Description:
  Sequence of SQL table names that are not included in your Django
  apps such as unmanaged models. Cachalot caches models that Django
  does not manage, so if you want to ignore/not-cache those models,
  then add them here.

``CACHALOT_QUERY_KEYGEN``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``'cachalot.utils.get_query_cache_key'``
:Description: Python module path to the function that will be used to generate
              the cache key of a SQL query.
              Run ``./manage.py invalidate_cachalot``
              after changing this setting.

``CACHALOT_TABLE_KEYGEN``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``'cachalot.utils.get_table_cache_key'``
:Description: Python module path to the function that will be used to generate
              the cache key of a SQL table.
              Clear your cache after changing this setting (it’s not enough
              to use ``./manage.py invalidate_cachalot``).

``CACHALOT_FINAL_SQL_CHECK``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Default: ``False``
:Description:
    If set to ``True``, the final SQL check will be performed.
    The `Final SQL check` checks for potentially overlooked tables when looking up involved tables
    (eg. Ordering by referenced table). See tests for more details
    (eg. ``test_order_by_field_of_another_table_with_check``).

    Enabling this setting comes with a small performance cost::

        CACHALOT_FINAL_SQL_CHECK=False:
            mysql      is 1.4× slower then 9.9× faster
            postgresql is 1.3× slower then 11.7× faster
            sqlite     is 1.4× slower then 3.0× faster
            filebased  is 1.4× slower then 9.5× faster
            locmem     is 1.3× slower then 11.3× faster
            pylibmc    is 1.4× slower then 8.5× faster
            pymemcache is 1.4× slower then 7.3× faster
            redis      is 1.4× slower then 6.8× faster

        CACHALOT_FINAL_SQL_CHECK=True:
            mysql      is 1.5× slower then 9.0× faster
            postgresql is 1.3× slower then 10.5× faster
            sqlite     is 1.4× slower then 2.6× faster
            filebased  is 1.4× slower then 9.1× faster
            locmem     is 1.3× slower then 9.9× faster
            pylibmc    is 1.4× slower then 7.5× faster
            pymemcache is 1.4× slower then 6.5× faster
            redis      is 1.5× slower then 6.2× faster



.. _Command:

``manage.py`` command
.....................

``manage.py invalidate_cachalot`` is available to invalidate all the cache keys
set by django-cachalot. If you run it without any argument, it invalidates all
models on all caches and all databases. But you can specify what applications
or models are invalidated, and on which cache or database.

Examples:

``./manage.py invalidate_cachalot auth``
    Invalidates all models from the 'auth' application.
``./manage.py invalidate_cachalot your_app auth.User``
    Invalidates all models from the 'your_app' application, but also
    the ``User`` model from the 'auth' application.
``./manage.py invalidate_cachalot -c redis -p postgresql``
    Invalidates all models,
    but only for the database configured with the 'postgresql' alias,
    and only for the cache configured with the 'redis' alias.


.. _Template utils:

Template utils
..............

`Caching template fragments <https://docs.djangoproject.com/en/dev/topics/cache/#template-fragment-caching>`_
can be extremely powerful to speedup a Django application.  However, it often
means you have to adapt your models to get a relevant cache key, typically
by adding a timestamp that refers to the last modification of the object.

But modifying your models and caching template fragments leads
to stale contents most of the time. There’s a simple reason to that: we rarely
only display the data from one model, we often want to display related data,
such as the number of books written by someone, display a quote from a book
of this author, display similar authors, etc. In such situations,
**it’s impossible to cache template fragments and avoid stale rendered data**.

Fortunately, django-cachalot provides an easy way to fix this issue,
by simply checking when was the last time data changed in the given models
or tables.  The API function
:meth:`get_last_invalidation <cachalot.api.get_last_invalidation>` does that,
and we provided a ``get_last_invalidation`` template tag to directly
use it in templates.  It works exactly the same as the API function.

Django template tag
~~~~~~~~~~~~~~~~~~~

Example of a quite heavy nested loop with a lot of SQL queries
(considering no prefetch has been done)::

    {% load cachalot cache %}

    {% get_last_invalidation 'auth.User' 'library.Book' 'library.Author' as last_invalidation %}
    {% cache 3600 short_user_profile last_invalidation %}
      {{ user }} has borrowed these books:
      {% for book in user.borrowed_books.all %}
        <div class="book">
          {{ book }} ({{ book.pages.count }} pages)
          <span class="authors">
            {% for author in book.authors.all %}
              {{ author }}{% if not forloop.last %},{% endif %}
            {% endfor %}
          </span>
        </div>
      {% endfor %}
    {% endcache %}

``cache_alias`` and ``db_alias`` keywords arguments of this template tag
are also available (see
:meth:`cachalot.api.get_last_invalidation`).

Jinja2 statement and function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Jinja2 extension for django-cachalot can be used, simply add
``'cachalot.jinja2ext.cachalot',`` to the ``'extensions'`` list of the ``OPTIONS``
dict in the Django ``TEMPLATES`` settings.

It provides:

- The API function
  :meth:`get_last_invalidation <cachalot.api.get_last_invalidation>` directly
  available as a function anywhere in Jinja2.
- An Jinja2 statement equivalent to the ``cache`` template tag of Django.

The ``cache`` does the same thing as its Django template equivalent,
except that ``cache_key`` and ``timeout`` are optional keyword arguments, and
you need to add commas between arguments. When unspecified, ``cache_key`` is
generated from the template filename plus the statement line number, and
``timeout`` defaults to infinite.  To specify which cache should store the
saved content, use the ``cache_alias`` keyword argument.

Same example than above, but for Jinja2::

    {% cache get_last_invalidation('auth.User', 'library.Book', 'library.Author'),
             cache_key='short_user_profile', timeout=3600 %}
      {{ user }} has borrowed these books:
      {% for book in user.borrowed_books.all() %}
        <div class="book">
          {{ book }} ({{ book.pages.count() }} pages)
          <span class="authors">
            {% for author in book.authors.all() %}
              {{ author }}{% if not loop.last %},{% endif %}
            {% endfor %}
          </span>
        </div>
      {% endfor %}
    {% endcache %}


.. _Signal:

Signal
......

``cachalot.signals.post_invalidation`` is available if you need to do something
just after a cache invalidation (when you modify something in a SQL table).
``sender`` is the name of the SQL table invalidated, and a keyword argument
``db_alias`` explains which database is affected by the invalidation.
Be careful when you specify ``sender``, as it is sensible to string type.
To be sure, use ``Model._meta.db_table``.

This signal is not directly triggered during transactions,
it waits until the current transaction ends.  This signal is also triggered
when invalidating using the API or the ``manage.py`` command.  Be careful
when using multiple databases, if you invalidate all databases by simply
calling ``invalidate()``, this signal will be triggered one time
for each database and for each model.  If you have 3 databases and 20 models,
``invalidate()`` will trigger the signal 60 times.

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
