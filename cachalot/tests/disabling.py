# coding: utf-8

from __future__ import unicode_literals
import datetime
from unittest import skipIf, skipUnless
from uuid import UUID
from decimal import Decimal

from django import VERSION as django_version
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Count
from django.db.models.expressions import RawSQL
from django.db.transaction import TransactionManagementError
from django.test import (
    TransactionTestCase, skipUnlessDBFeature, override_settings)
from pytz import UTC

from ..monkey_patch import DISABLE_CACHING
from ..settings import cachalot_settings
from ..utils import UncachableQuery
from .models import Test, TestChild, TestParent
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
            n1 = bool(Test.objects.exists())  # Force the query to run
        # Caching disabled so this query shouldn't be cached
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                n2 = bool(Test.objects.exists())  # Force the query to run

    def test_read_toggle_disabling_using_with_stmt(self):
        with self.assertNumQueries(1):
            n1 = bool(Test.objects.exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                n2 = bool(Test.objects.exists())  # Force the query to run
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            n3 = bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(0):
            n4 = bool(Test.objects.exists())  # Force the query to run

    def test_read_toggle_disabling_without_invalidating_using_with_stmt(self):
        with self.assertNumQueries(1):
            n1 = bool(Test.objects.exists())  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.do_not_invalidate()
            with self.assertNumQueries(1):
                n2 = bool(Test.objects.exists())  # Force the query to run
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            n3 = bool(Test.objects.exists())  # Force the query to run

    def test_read_disabling_using_try_finally(self):
        with self.assertNumQueries(1):
            n1 = bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        err = None
        # Caching disabled so this query shouldn't be cached
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                n2 = bool(Test.objects.exists())  # Force the query to run
        except Exception as err:
            blew_up = True
        finally:
            DISABLE_CACHING.disable()
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(err))

    def test_read_toggle_disabling_using_try_finally(self):
        with self.assertNumQueries(1):
            n1 = bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        err = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                n2 = bool(Test.objects.exists())  # Force the query to run
        except Exception as err:
            blew_up = True
        finally:
            DISABLE_CACHING.disable()
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(err))
        # Caching enabled but invalidating has run
        with self.assertNumQueries(1):
            n3 = bool(Test.objects.exists())  # Force the query to run
        with self.assertNumQueries(0):
            n4 = bool(Test.objects.exists())  # Force the query to run

    def test_read_toggle_disabling_without_invalidating_using_try_finally(self):
        with self.assertNumQueries(1):
            n1 = bool(Test.objects.exists())  # Force the query to run
        blew_up = False
        err = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                n2 = bool(Test.objects.exists())  # Force the query to run
        except Exception as err:
            blew_up = True
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(err))
        # Caching enabled without invalidating so this query should be cached
        with self.assertNumQueries(0):
            n3 = bool(Test.objects.exists())  # Force the query to run

    def test_write_disabling_using_with_stmt(self):
        data1 = Test.objects.get(name='test1')
        data1_name = data1.name  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                data1.name = 'test1a'
                data1.save()
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            data2 = Test.objects.get(name='test1a')
            data2_name = data2.name  # Force the query to run
        with self.assertNumQueries(0):
            data3 = Test.objects.get(name='test1a')
            data3_name = data3.name  # Force the query to run
        # Reset the name to test1
        data1.name = 'test1'
        data1.save()

    # HOPEFULLY NO ONE EVER DOES THIS IN PRODUCTION CODE.
    def test_write_disabling_without_invalidating_using_with_stmt(self):
        data1 = Test.objects.get(name='test1')
        data1_name = data1.name  # Force the query to run
        # Disable the cache
        with DISABLE_CACHING:
            DISABLE_CACHING.do_not_invalidate()
            with self.assertNumQueries(1):
                data1.name = 'test1a'
                data1.save()
        # Caching enabled without invalidating so this query should
        # be cached even though the object is no longer named test1.
        with self.assertNumQueries(0):
            data2 = Test.objects.get(name='test1')
            data2_name = data2.name  # Force the query to run
        with self.assertNumQueries(1):
            data3 = Test.objects.get(name='test1a')
            data3_name = data3.name  # Force the query to run
        data1.name = 'test1'
        data1.save()

    def test_write_disabling_using_try_finally(self):
        data1 = Test.objects.get(name='test1')
        data1_name = data1.name  # Force the query to run
        blew_up = False
        err = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                data1.name = 'test1a'
                data1.save()
        except Exception as err:
            blew_up = True
        finally:
            DISABLE_CACHING.disable()
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(err))
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            data2 = Test.objects.get(name='test1a')
            data2_name = data2.name  # Force the query to run
        with self.assertNumQueries(0):
            data3 = Test.objects.get(name='test1a')
            data3_name = data3.name  # Force the query to run
        # Reset the name to test1
        data1.name = 'test1'
        data1.save()

    # HOPEFULLY NO ONE EVER DOES THIS IN PRODUCTION CODE.
    def test_write_disabling_without_invalidating_using_try_finally(self):
        data1 = Test.objects.get(name='test1')
        data1_name = data1.name  # Force the query to run
        blew_up = False
        err = None
        # Disable the cache
        try:
            DISABLE_CACHING.enable()
            with self.assertNumQueries(1):
                data1.name = 'test1a'
                data1.save()
        except Exception as err:
            blew_up = True
        finally:
            DISABLE_CACHING.disable(invalidate_cache=False)
        self.assertFalse(blew_up, msg='Unexpected Exception Occurred: {0}'.format(err))
        # Caching enabled without invalidating so this query should
        # be cached even though the object is no longer named test1.
        with self.assertNumQueries(0):
            data2 = Test.objects.get(name='test1')
            data2_name = data2.name  # Force the query to run
        with self.assertNumQueries(1):
            data3 = Test.objects.get(name='test1a')
            data3_name = data3.name  # Force the query to run
        data1.name = 'test1'
        data1.save()

    def test_raw_read_toggle_disabling_using_with_stmt(self):
        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM cachalot_test where name = %s", 'test1')
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM cachalot_test where name = %s", 'test1')
        # Caching enabled, invalidating has run
        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM cachalot_test where name = %s", 'test1')
        with self.assertNumQueries(0):
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM cachalot_test where name = %s", 'test1')

    def test_raw_read_toggle_disabling_without_invalidating_using_with_stmt(self):
        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM cachalot_test where name = %s", 'test1')
        # Disable the cache
        with DISABLE_CACHING:
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM cachalot_test where name = %s", 'test1')
        # Caching enabled, invalidating has run
        with self.assertNumQueries(0):
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM cachalot_test where name = %s", 'test1')
