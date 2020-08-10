Thanks for contributing to Django Cachalot!

We appreciate any support in improvements to this system
in performance, erasing dependency errors, or in killing bugs.

When you start a PR or issue, please follow the layout provided.

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
