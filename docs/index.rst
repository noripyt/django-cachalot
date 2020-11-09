***************
django-cachalot
***************

Caches your Django ORM queries and automatically invalidates them.

.. image:: https://raw.github.com/noripyt/django-cachalot/master/django-cachalot.jpg

----

.. image:: http://img.shields.io/pypi/v/django-cachalot.svg?style=flat-square&maxAge=3600
   :target: https://pypi.python.org/pypi/django-cachalot

.. image:: http://img.shields.io/travis/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://travis-ci.org/noripyt/django-cachalot

.. image:: http://img.shields.io/coveralls/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://coveralls.io/r/noripyt/django-cachalot?branch=master

.. image:: http://img.shields.io/scrutinizer/g/noripyt/django-cachalot/master.svg?style=flat-square&maxAge=3600
   :target: https://scrutinizer-ci.com/g/noripyt/django-cachalot/

.. image:: https://img.shields.io/discord/773656139207802881
    :target: https://discord.gg/WFGFBk8rSU

Usage
.....

#. ``pip install django-cachalot``
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. If you use multiple servers with a common cache server,
   :ref:`double check their clock synchronisation <https://django-cachalot.readthedocs.io/en/latest/limits.html#multiple-servers>`_
#. If you modify data outside Django
   – typically after restoring a SQL database –,
   use the :ref:`manage.py command <https://django-cachalot.readthedocs.io/en/latest/quickstart.html#command>`_
#. Be aware of :ref:`the few other limits <https://django-cachalot.readthedocs.io/en/latest/limits.html#limits>`_
#. If you use
   `django-debug-toolbar <https://github.com/jazzband/django-debug-toolbar>`_,
   you can add ``'cachalot.panels.CachalotPanel',``
   to your ``DEBUG_TOOLBAR_PANELS``
#. Enjoy!

Note: In settings, you can use `CACHALOT_UNCACHABLE_TABLES <https://django-cachalot.readthedocs.io/en/latest/quickstart.html#cachalot-only-cachable-tables>`_ as a frozenset of table names (e.g. "public_test" if public was the app name and test is a model name).

Why use cachalot? `Check out our comparison <https://django-cachalot.readthedocs.io/en/latest/introduction.html#comparison-with-similar-tools>`_

Below the tree is an in-depth opinion from the new maintainer:

.. toctree::
   :maxdepth: 2

   introduction
   quickstart
   limits
   api
   benchmark
   todo
   reporting
   how
   legacy
   changelog

In-depth opinion (from new maintainer):

There are three main third party caches: cachalot, cache-machine, and cache-ops. Which do you use? We suggest a mix:

TL;DR Use cachalot for cold or modified <50 times per minutes (Most people should stick with only cachalot since you
most likely won't need to scale to the point of needing cache-machine added to the bowl). If you're an enterprise that
already has huge statistics, then mixing cold caches for cachalot and your hot caches with cache-machine is the best
mix. However, when performing joins with select_related and prefetch_related, you can
get a nearly 100x speed up for your initial deployment.

Recall, cachalot caches THE ENTIRE TABLE. That's where its inefficiency stems from: if you keep updating the records,
then the cachalot constantly invalidates the table and re-caches. Luckily caching is very efficient, it's just the cache
invalidation part that kills all our systems. Look at Note 1 below to see how Reddit deals with it.

Cachalot is more-or-less intended for cold caches or "just-right" conditions. If you find a partition library for
Django (also authored but work-in-progress by `Andrew Chen Wang <https://github.com/Andrew-Chen-Wang>`_),
then the caching will work better since sharding the cold/accessed-the-least records aren't invalidated as much.

Cachalot is good when there are <50 modifications per minute on a hot cached table. This is mostly due to cache invalidation. It's the same with any cache,
which is why we suggest you use cache-machine for hot caches. Cache-machine caches individual objects, taking up more in the memory store but
invalidates those individual objects instead of the entire table like cachalot.

Yes, the bane of our entire existence lies in cache invalidation and naming variables. Why does cachalot suck when stuck
with a huge table that's modified rapidly? Since you've mixed your cold (90% of) with your hot (10% of) records, you're
caching and invalidating an entire table. It's like trying to boil 1 ton of noodles inside ONE pot instead of 100 pots
boiling 1 ton of noodles. Which is more efficient? The splitting up of them.

Note 1: My personal experience with caches stems from Reddit's: https://redditblog.com/2017/01/17/caching-at-reddit/
