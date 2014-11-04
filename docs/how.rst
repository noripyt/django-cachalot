How django-cachalot works
-------------------------

.. note:: If you don’t understand, just pretend it’s magic.

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
