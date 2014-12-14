How django-cachalot works
-------------------------

.. note:: If you don’t understand, you can pretend it’s magic.

Reverse engineering
...................

It’s a lot of Django reverse engineering combined with a strong test suite.
Such a test suite is crucial for a reverse engineering project.
If some important part of Django changes and breaks the expected behaviour,
you can be sure that the test suite will fail.

Monkey patching
...............

Django-cachalot modifies Django in place during execution to add a caching tool
just before SQL queries are executed.
When a SQL query reads data, we save the result in cache. If that same query is
executed later, we fetch that result from cache.
When we detect ``INSERT``, ``UPDATE`` or ``DELETE``, we know which tables are
modified. All the previous cached queries can therefore be safely invalidated.
