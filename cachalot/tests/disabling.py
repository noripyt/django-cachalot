# coding: utf-8

from __future__ import unicode_literals
from unittest import skipIf

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.db import connection, connections, DEFAULT_DB_ALIAS
from django.test import TransactionTestCase
from ..api import invalidate
from ..monkey_patch import DISABLE_CACHING
from .models import Test
from .test_utils import TestUtilsMixin


class DisablingTestCase(TestUtilsMixin, TransactionTestCase):
    """
    Test the number of queries run while switching between
    caching being enabled and disabled.

    Test both forms of use (with statement and try finally).

    Test that things invalidate after enabling.

    Test that things are still cached if we don't invalidate after
    enabling.

    Make sure that the sql gets run on the line where we create it
    so that sql runs exactly where the test specifies the query.
    This way we don't have issues where an sql query doesn't get
    executed until you use it in an assert test.
    """

    def setUp(self):
        super(DisablingTestCase, self).setUp()

        self.group = Group.objects.create(name='test_group')
        self.group__permissions = list(Permission.objects.all()[:3])
        self.group.permissions.add(*self.group__permissions)
        self.user = User.objects.create_user('user')
        self.user__permissions = list(Permission.objects.all()[3:6])
        self.user.groups.add(self.group)
        self.user.user_permissions.add(*self.user__permissions)
        self.admin = User.objects.create_superuser('admin', 'admin@test.me',
                                                   'password')
        self.t1__permission = (Permission.objects.order_by('?')
                               .select_related('content_type')[0])
        self.t1 = Test.objects.create(
            name='test1', owner=self.user,
            date='1789-07-14', datetime='1789-07-14T16:43:27',
            permission=self.t1__permission)
        self.t2 = Test.objects.create(
            name='test2', owner=self.admin, public=True,
            date='1944-06-06', datetime='1944-06-06T06:35:00')

    def test_read_disabling_using_with_stmt(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                bool(Test.objects.exists())  # Force the query to run
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run

    def test_read_disabling_without_invalidating_using_with_stmt(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.do_not_invalidate()
            with self.assertNumQueries(1):
                bool(Test.objects.exists())  # Force the query to run
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run

    def test_read_disabling_using_try_finally(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                bool(Test.objects.exists())  # Force the query to run
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable()
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled but invalidating has run
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run

    def test_read_disabling_without_invalidating_using_try_finally(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                bool(Test.objects.exists())  # Force the query to run
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run

    def test_write_disabling_using_with_stmt(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.get(name='test1')
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(2 if self.is_sqlite else 1):
                data1.name = 'test1a'
                data1.save()
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')
        with self.assertNumQueries(0):
            Test.objects.get(name='test1a')

    # HOPEFULLY NO ONE EVER DOES THIS IN PRODUCTION CODE.
    def test_write_disabling_without_invalidating_using_with_stmt(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.get(name='test1')
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.do_not_invalidate()
            with self.assertNumQueries(2 if self.is_sqlite else 1):
                data1.name = 'test1a'
                data1.save()
        # Caching enabled without invalidating so this query should
        # be cached even though the object is no longer named test1.
        with self.assertNumQueries(0):
            Test.objects.get(name='test1')
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')

    def test_write_disabling_using_try_finally(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.get(name='test1')
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(2 if self.is_sqlite else 1):
                data1.name = 'test1a'
                data1.save()
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable()
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')
        with self.assertNumQueries(0):
            Test.objects.get(name='test1a')

    # HOPEFULLY NO ONE EVER DOES THIS IN PRODUCTION CODE.
    def test_write_disabling_without_invalidating_using_try_finally(self):
        data1 = Test.objects.get(name='test1')
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(2 if self.is_sqlite else 1):
                data1.name = 'test1a'
                data1.save()
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled without invalidating so this query should
        # be cached even though the object is no longer named test1.
        with self.assertNumQueries(0):
            Test.objects.get(name='test1')
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')

    def test_raw_read_disabling_using_with_stmt(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM cachalot_test where name = %s", ('test1', ))
                    tuple(cursor.fetchall())
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')

    def test_raw_read_disabling_without_invalidating_using_with_stmt(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        # Disable the cache
        with self.assertNumQueries(1):
            with DISABLE_CACHING:
                DISABLE_CACHING.do_not_invalidate()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM cachalot_test where name = %s", ('test1', ))
        # Caching enabled, invalidating has run
        with self.assertNumQueries(0):
            Test.objects.get(name='test1')

    def test_raw_read_disabling_using_try_finally(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            with self.assertNumQueries(1):
                DISABLE_CACHING.enable()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM cachalot_test where name = %s", ('test1', ))
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable()
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled but invalidating has run
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')

    def test_raw_read_disabling_without_invalidating_using_try_finally(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM cachalot_test where name = %s", ('test1', ))
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            Test.objects.get(name='test1')

    def test_raw_write_disabling_using_with_stmt(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE cachalot_test set name = %s where name = %s", ('test1a', 'test1'))
        # Caching enabled, invalidating has run
        with self.assertRaises(Test.DoesNotExist):
            Test.objects.get(name='test1')
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')

    def test_raw_write_disabling_without_invalidating_using_with_stmt(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.do_not_invalidate()
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE cachalot_test set name = %s where name = %s", ('test1a', 'test1'))
        # Caching enabled without invalidating so this query should
        # be cached even though the object is no longer named test1.
        with self.assertNumQueries(0):
            Test.objects.get(name='test1')
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')

    def test_raw_write_disabling_using_try_finally(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        blew_up = False
        err = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE cachalot_test set name = %s where name = %s", ('test1a', 'test1'))
        except Exception as err:
            blew_up = True
        finally:
            DISABLE_CACHING.disable()
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(err))
        # Caching enabled, invalidating has run
        with self.assertRaises(Test.DoesNotExist):
            Test.objects.get(name='test1')
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')

    def test_raw_write_disabling_without_invalidating_using_try_finally(self):
        with self.assertNumQueries(1):
            Test.objects.get(name='test1')
        blew_up = False
        err = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE cachalot_test set name = %s where name = %s", ('test1a', 'test1'))
        except Exception as err:
            blew_up = True
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(err))
        # Caching enabled without invalidating so this query should
        # be cached even though the object is no longer named test1.
        with self.assertNumQueries(0):
            Test.objects.get(name='test1')
        with self.assertNumQueries(1):
            Test.objects.get(name='test1a')

    def test_clear_using_with_stmt(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:  # Since we are clearing below this shouldn't invalidate on exit.
            # Clear the disabling class - This really shouldn't be used unless absolutely necessary.
            # It was designed just as an in case anyone ever needs it function.
            DISABLE_CACHING.clear()
            with self.assertNumQueries(0):
                bool(Test.objects.exists())  # Force the query to run

        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run

    def test_clear_using_try_finally(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            # Clear the disabling class - This really shouldn't be used unless absolutely necessary.
            # It was designed just as an in case anyone ever needs it function.
            DISABLE_CACHING.clear()
            with self.assertNumQueries(0):
                bool(Test.objects.exists())  # Force the query to run
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable()  # Since we cleared this shouldn't invalidate
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run


@skipIf(len(settings.DATABASES) == 1,
        'We can’t change the DB used since there’s only one configured')
class DisablingMultiDatabaseTestCase(TransactionTestCase):
    multi_db = True

    def setUp(self):
        self.t1 = Test.objects.create(name='test1')
        self.t2 = Test.objects.create(name='test2')
        self.db_alias2 = next(alias for alias in settings.DATABASES
                              if alias != DEFAULT_DB_ALIAS)
        connection2 = connections[self.db_alias2]
        self.is_sqlite2 = connection2.vendor == 'sqlite'
        self.is_mysql2 = connection2.vendor == 'mysql'
        if connection2.vendor in ('mysql', 'postgresql'):
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection2.cursor()

    def test_read_disabling_one_db_using_with_stmt(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.set_aliases(db_alias=self.db_alias2)
            with self.assertNumQueries(1, using=self.db_alias2):
                bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        # Caching enabled, invalidating has run
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run

    def test_read_disabling_without_invalidating_one_db_using_with_stmt(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.do_not_invalidate()
            DISABLE_CACHING.set_aliases(db_alias=self.db_alias2)
            with self.assertNumQueries(1, using=self.db_alias2):
                bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run

    def test_read_disabling_one_db_using_try_finally(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1, using=self.db_alias2):
                bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable(db_alias=self.db_alias2)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        # Caching enabled but invalidating has run
        with self.assertNumQueries(1, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run

    def test_read_disabling_one_db_without_invalidating_using_try_finally(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1, using=self.db_alias2):
                bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False, db_alias=self.db_alias2)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        # Caching enabled but invalidating has run
        with self.assertNumQueries(0, using=self.db_alias2):
            bool(Test.objects.using(self.db_alias2).exists())  # Force the query to run


@skipIf(len(settings.CACHES) == 1,
        'We can’t change the cache used since there’s only one configured')
class DisablingMultiCacheTestCase(TransactionTestCase):
    multi_db = True

    def setUp(self):
        self.cache_alias2 = next(alias for alias in settings.CACHES
                                 if alias != DEFAULT_CACHE_ALIAS)

        self.t1 = Test.objects.create(name='test1')
        self.t2 = Test.objects.create(name='test2')

        # Start each tests with a fresh cache
        invalidate('cachalot_test')

    def test_read_disabling_one_cache_using_with_stmt(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.set_aliases(cache_alias=self.cache_alias2)
            with self.assertNumQueries(1):
                with self.settings(CACHALOT_CACHE=self.cache_alias2):
                    bool(Test.objects.exists())  # Force the query to run
        # Caching enabled, invalidating has run
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run

    def test_read_disabling_without_invalidating_one_db_using_with_stmt(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.do_not_invalidate()
            DISABLE_CACHING.set_aliases(cache_alias=self.cache_alias2)
            with self.assertNumQueries(1):
                with self.settings(CACHALOT_CACHE=self.cache_alias2):
                    bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(0):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run

    def test_read_disabling_one_db_using_try_finally(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                with self.settings(CACHALOT_CACHE=self.cache_alias2):
                    bool(Test.objects.exists())  # Force the query to run
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable(cache_alias=self.cache_alias2)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        # Caching enabled but invalidating has run
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run

    def test_read_disabling_one_db_without_invalidating_using_try_finally(self):
        with self.assertNumQueries(1):
            bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(1):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        error_message = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                with self.settings(CACHALOT_CACHE=self.cache_alias2):
                    bool(Test.objects.exists())  # Force the query to run
        except Exception as err:  # In python 3 err is deleted after this block
            blew_up = True
            error_message = err
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False, cache_alias=self.cache_alias2)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(error_message))
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            bool(Test.objects.exists())  # Force the query to run
        # Caching enabled but invalidating has run
        with self.assertNumQueries(0):
            with self.settings(CACHALOT_CACHE=self.cache_alias2):
                bool(Test.objects.exists())  # Force the query to run
