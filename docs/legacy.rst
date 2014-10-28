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
