.. _limits:

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

If you modify the database using a raw query, **you will have to manually
invalidate** django-cachalot using one of the tools available in :ref:`the API <API>`.
