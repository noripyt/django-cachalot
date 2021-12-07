Django Cachalot
===============

Caches your Django ORM queries and automatically invalidates them.

Documentation: http://django-cachalot.readthedocs.io

----

.. image:: http://img.shields.io/pypi/v/django-cachalot.svg?style=flat-square&maxAge=3600
   :target: https://pypi.python.org/pypi/django-cachalot

.. image:: https://img.shields.io/pypi/pyversions/django-cachalot
    :target: https://django-cachalot.readthedocs.io/en/latest/

.. image:: https://github.com/noripyt/django-cachalot/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/noripyt/django-cachalot/actions/workflows/ci.yml

.. image:: http://img.shields.io/coveralls/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://coveralls.io/r/noripyt/django-cachalot?branch=master

.. image:: http://img.shields.io/scrutinizer/g/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://scrutinizer-ci.com/g/noripyt/django-cachalot/

.. image:: https://img.shields.io/discord/773656139207802881
    :target: https://discord.gg/WFGFBk8rSU

----

Table of Contents:

- Quickstart
- Usage
- Hacking
- Benchmark
- Third-Party Cache Comparison
- Discussion

Quickstart
----------

Cachalot officially supports Python 3.7-3.10 and Django 2.2, 3.2, and 4.0 with the databases PostgreSQL, SQLite, and MySQL.

Note: an upper limit on Django version is set for your safety. Please do not ignore it.

Usage
-----

#. ``pip install django-cachalot``
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. If you use multiple servers with a common cache server,
   `double check their clock synchronisation <https://django-cachalot.readthedocs.io/en/latest/limits.html#multiple-servers>`_
#. If you modify data outside Django
   – typically after restoring a SQL database –,
   use the `manage.py command <https://django-cachalot.readthedocs.io/en/latest/quickstart.html#command>`_
#. Be aware of `the few other limits <https://django-cachalot.readthedocs.io/en/latest/limits.html#limits>`_
#. If you use
   `django-debug-toolbar <https://github.com/jazzband/django-debug-toolbar>`_,
   you can add ``'cachalot.panels.CachalotPanel',``
   to your ``DEBUG_TOOLBAR_PANELS``
#. Enjoy!

Hacking
-------

To start developing, install the requirements
and run the tests via tox.

Make sure you have the following services:

* Memcached
* Redis
* PostgreSQL
* MySQL

For setup:

#. Install: ``pip install -r requirements/hacking.txt``
#. For PostgreSQL: ``CREATE ROLE cachalot LOGIN SUPERUSER;``
#. Run: ``tox --current-env`` to run the test suite on your current Python version.
#. You can also run specific databases and Django versions: ``tox -e py38-django3.1-postgresql-redis``

Benchmark
---------

Currently, benchmarks are supported on Linux and Mac/Darwin.
You will need a database called "cachalot" on MySQL and PostgreSQL.
Additionally, on PostgreSQL, you will need to create a role
called "cachalot." You can also run the benchmark, and it'll raise
errors with specific instructions for how to fix it.

#. Install: ``pip install -r requirements/benchmark.txt``
#. Run: ``python benchmark.py``

The output will be in benchmark/TODAY'S_DATE/

TODO Create Docker-compose file to allow for easier running of data.

Third-Party Cache Comparison
----------------------------

There are three main third party caches: cachalot, cache-machine, and cache-ops. Which do you use? We suggest a mix:

TL;DR Use cachalot for cold or modified <50 times per minutes (Most people should stick with only cachalot since you
most likely won't need to scale to the point of needing cache-machine added to the bowl). If you're an enterprise that
already has huge statistics, then mixing cold caches for cachalot and your hot caches with cache-machine is the best
mix. However, when performing joins with ``select_related`` and ``prefetch_related``, you can
get a nearly 100x speed up for your initial deployment.

Recall, cachalot caches THE ENTIRE TABLE. That's where its inefficiency stems from: if you keep updating the records,
then the cachalot constantly invalidates the table and re-caches. Luckily caching is very efficient, it's just the cache
invalidation part that kills all our systems. Look at Note 1 below to see how Reddit deals with it.

Cachalot is more-or-less intended for cold caches or "just-right" conditions. If you find a partition library for
Django (also authored but work-in-progress by `Andrew Chen Wang`_), then the caching will work better since sharding
the cold/accessed-the-least records aren't invalidated as much.

Cachalot is good when there are <50 modifications per minute on a hot cached table. This is mostly due to cache invalidation. It's the same with any cache,
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

Help? Technical chat? `It's here on Discord <https://discord.gg/WFGFBk8rSU>`_.

Legacy chats:

- https://gitter.im/django-cachalot/Lobby
- https://join.slack.com/t/cachalotdjango/shared_invite/zt-dd0tj27b-cIH6VlaSOjAWnTG~II5~qw

.. _Andrew Chen Wang: https://github.com/Andrew-Chen-Wang

.. image:: https://raw.github.com/noripyt/django-cachalot/master/django-cachalot.jpg
