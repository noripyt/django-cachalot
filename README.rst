**New Maintainer**: `Andrew Chen Wang`_ is a new maintainer of this repo. Bordage is still the admin but will most likely be inactive.

Django Cachalot
===============

Caches your Django ORM queries and automatically invalidates them.

Documentation: http://django-cachalot.readthedocs.io

----

.. image:: http://img.shields.io/pypi/v/django-cachalot.svg?style=flat-square&maxAge=3600
   :target: https://pypi.python.org/pypi/django-cachalot

.. image:: http://img.shields.io/travis/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://travis-ci.org/noripyt/django-cachalot

.. image:: http://img.shields.io/coveralls/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://coveralls.io/r/noripyt/django-cachalot?branch=master

.. image:: http://img.shields.io/scrutinizer/g/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://scrutinizer-ci.com/g/noripyt/django-cachalot/

.. image:: https://img.shields.io/badge/cachalot-Chat%20on%20Slack-green?style=flat&logo=slack
    :target: https://join.slack.com/t/cachalotdjango/shared_invite/enQtOTMyNzI0NTQzOTA3LWViYmYwMWY3MmU0OTZkYmNiMjBhN2NjNjc4OWVlZDNiMjMxN2Y3YzljYmNiYTY4ZTRjOGQxZDRiMTM0NWE3NGI

Quickstart
----------

Cachalot officially supports Python 2.7, 3.4-3.8 and Django 1.11, 2.0-2.2, 3.0 with the databases PostgreSQL, SQLite, and MySQL.

Note: Python 3.4 with MySQL fails on tests. If you're MySQL is configured correctly,

Third-Party Cache Comparison
----------------------------

There are three main third party caches: cachalot, cache-machine, and cache-ops. Which do you use? We suggest a mix:

TL;DR Use cachalot for cold or modified <50 times per seconds (Most people should stick with only cachalot since you
most likely won't need to scale to the point of needing cache-machine added to the bowl). If you're an enterprise that
already has huge statistics, then mixing cold caches for cachalot and your hot caches with cache-machine is the best
mix.

Recall, cachalot caches THE ENTIRE TABLE. That's where its inefficiency stems from: if you keep updating the records,
then the cachalot constantly invalidates the table and re-caches. Luckily caching is very efficient, it's just the cache
invalidation part that kills all our systems. Look at Note 1 below to see how Reddit deals with it.

Cachalot is more-or-less intended for cold caches or "just-right" conditions. If you find a partition library for
Django (also authored but work-in-progress by `Andrew Chen Wang`_), then the caching will work better since sharding
the cold/accessed-the-least records aren't invalidated as much.

Cachalot is good when there are <50 modifications per second on a hot cached table. This is mostly due to cache invalidation. It's the same with any cache,
which is why we suggest you use cache-machine for hot caches. Cache-machine caches individual objects, taking up more in the memory store but
invalidates those individual objects instead of the entire table like cachalot.

Yes, the bane of our entire existence lies in cache invalidation and naming variables. Why does cachalot suck when
stuck with a huge table that's modified rapidly? Since you've mixed your cold (90% of) with your hot (10% of) records,
you're caching and invalidating an entire table. It's like trying to boil 1 ton of noodles inside ONE pot instead of
100 pots boiling 1 ton of noodles. Which is more efficient? The splitting up of them.

Note 1: My personal experience with caches stems from Reddit's: https://redditblog.com/2017/01/17/caching-at-reddit/

Note 2: Technical comparison: https://django-cachalot.readthedocs.io/en/latest/introduction.html#comparison-with-similar-tools

Discussion
----------

Help? Technical chat? `It's here on Slack <https://join.slack.com/t/cachalotdjango/shared_invite/enQtOTMyNzI0NTQzOTA3LWViYmYwMWY3MmU0OTZkYmNiMjBhN2NjNjc4OWVlZDNiMjMxN2Y3YzljYmNiYTY4ZTRjOGQxZDRiMTM0NWE3NGI>`_.

Legacy chat: https://gitter.im/django-cachalot/Lobby

.. _Andrew Chen Wang: https://github.com/Andrew-Chen-Wang

.. image:: https://raw.github.com/noripyt/django-cachalot/master/django-cachalot.jpg
