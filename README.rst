Django-cachalot
===============

Caches your Django ORM queries and automatically invalidates them.

**In alpha, do not use for production**

.. image:: https://raw.github.com/BertrandBordage/django-cachalot/master/django-cachalot.jpg


Quick start
-----------

Requirements
............

Django-cachalot currently requires Django 1.6
and `django-redis <https://github.com/niwibe/django-redis>`_ as your default
cache backend.  It should work with both Python 2 & 3.

Usage
.....

#. `pip install -e git+https://github.com/BertrandBordage/django-cachalot#egg=django-cachalot`
#. Add ``'cachalot',`` to your ``INSTALLED_APPS``
#. Enjoy!


What still needs to be done
---------------------------

- Correctly invalidate ``.extra`` queries
- Handle transactions
- Handle multiple database
- Write tests, including multi-table inheritance, prefetch_related, etc
- Find out if it’s thread-safe and test it
- Add a ``CACHALOT_ENABLED`` setting
- Add a setting to choose a cache other than ``'default'``
- Add support for other caches like memcached
