# coding: utf-8

from __future__ import unicode_literals

import datetime
from threading import Thread
from time import sleep
try:
    from unittest import skip, skipIf
except ImportError:  # For Python 2.6
    from unittest2 import skip, skipIf

from django.conf import settings
from django.contrib.auth.models import User, Permission, Group
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction, connection
from django.db.models import (
    Model, CharField, ForeignKey, BooleanField,
    DateField, DateTimeField, Count)
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from .settings import cachalot_settings


class Test(Model):
    name = CharField(max_length=20)
    owner = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    public = BooleanField(default=False)
    date = DateField(null=True, blank=True)
    datetime = DateTimeField(null=True, blank=True)
    permission = ForeignKey('auth.Permission', null=True, blank=True)

    class Meta(object):
        ordering = ('name',)


class ReadTestCase(TransactionTestCase):
    """
    Tests if every SQL request that only reads data is cached.

    The only exception is for requests that don’t go through the ORM, using
    ``QuerySet.extra`` with ``select`` or ``where`` arguments,
     ``Model.objects.raw``, or ``cursor.execute``.
    """

    def setUp(self):
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

    def test_empty(self):
        with self.assertNumQueries(0):
            data1 = list(Test.objects.none())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.none())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [])

    def test_exists(self):
        with self.assertNumQueries(1):
            n1 = Test.objects.exists()
        with self.assertNumQueries(0):
            n2 = Test.objects.exists()
        self.assertEqual(n2, n1)
        self.assertTrue(n2)

    def test_count(self):
        with self.assertNumQueries(1):
            n1 = Test.objects.count()
        with self.assertNumQueries(0):
            n2 = Test.objects.count()
        self.assertEqual(n2, n1)
        self.assertEqual(n2, 2)

    def test_get(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.get(name='test1')
        with self.assertNumQueries(0):
            data2 = Test.objects.get(name='test1')
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t1)

    def test_first(self):
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.filter(name='bad').first(), None)
        with self.assertNumQueries(0):
            self.assertEqual(Test.objects.filter(name='bad').first(), None)

        with self.assertNumQueries(1):
            data1 = Test.objects.first()
        with self.assertNumQueries(0):
            data2 = Test.objects.first()
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t1)

    def test_last(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.last()
        with self.assertNumQueries(0):
            data2 = Test.objects.last()
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t2)

    def test_all(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

    def test_filter(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(public=True))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(public=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2])

        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(name__in=['test2', 'test72']))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(name__in=['test2', 'test72']))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2])

    def test_filter_empty(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(public=True,
                                             name='user'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(public=True,
                                             name='user'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [])

    def test_exclude(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.exclude(public=True))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.exclude(public=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1])

        with self.assertNumQueries(1):
            data1 = list(Test.objects.exclude(name__in=['test2', 'test72']))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.exclude(name__in=['test2', 'test72']))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1])

    def test_slicing(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all()[:1])
        with self.assertNumQueries(0):
            data2 = list(Test.objects.all()[:1])
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1])

    def test_order_by(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.order_by('pk'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.order_by('pk'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

        with self.assertNumQueries(1):
            data1 = list(Test.objects.order_by('-name'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.order_by('-name'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2, self.t1])

    def test_reverse(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.reverse())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.reverse())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2, self.t1])

    def test_distinct(self):
        # We ensure that the query without distinct should return duplicate
        # objects, in order to have a real-world example.
        data1 = list(Test.objects.filter(
            owner__user_permissions__content_type__app_label='auth'))
        self.assertEqual(len(data1), 3)
        self.assertListEqual(data1, [self.t1] * 3)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.filter(
                owner__user_permissions__content_type__app_label='auth'
            ).distinct())
        with self.assertNumQueries(0):
            data3 = list(Test.objects.filter(
                owner__user_permissions__content_type__app_label='auth'
            ).distinct())
        self.assertListEqual(data3, data2)
        self.assertEqual(len(data3), 1)
        self.assertListEqual(data3, [self.t1])

    def test_iterator(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.iterator())
        with self.assertNumQueries(0):
            data2 = list(Test.objects.iterator())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

    def test_in_bulk(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.in_bulk((5432, self.t2.pk, 9200))
        with self.assertNumQueries(0):
            data2 = Test.objects.in_bulk((5432, self.t2.pk, 9200))
        self.assertDictEqual(data2, data1)
        self.assertDictEqual(data2, {self.t2.pk: self.t2})

    def test_values(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values('name', 'public'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values('name', 'public'))
        self.assertEqual(len(data1), 2)
        self.assertEqual(len(data2), 2)
        for row1, row2 in zip(data1, data2):
            self.assertDictEqual(row2, row1)
        self.assertDictEqual(data2[0], {'name': 'test1', 'public': False})
        self.assertDictEqual(data2[1], {'name': 'test2', 'public': True})

    def test_values_list(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('name', flat=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, ['test1', 'test2'])

    def test_earliest(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.earliest('date')
        with self.assertNumQueries(0):
            data2 = Test.objects.earliest('date')
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t1)

    def test_latest(self):
        with self.assertNumQueries(1):
            data1 = Test.objects.latest('date')
        with self.assertNumQueries(0):
            data2 = Test.objects.latest('date')
        self.assertEqual(data2, data1)
        self.assertEqual(data2, self.t2)

    def test_dates(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.dates('date', 'year'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.dates('date', 'year'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [datetime.date(1789, 1, 1),
                                     datetime.date(1944, 1, 1)])

    def test_datetimes(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.datetimes('datetime', 'hour'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.datetimes('datetime', 'hour'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [datetime.datetime(1789, 7, 14, 16),
                                     datetime.datetime(1944, 6, 6, 6)])

    def test_subquery(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(owner__in=User.objects.all()))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(owner__in=User.objects.all()))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

        with self.assertNumQueries(1):
            data3 = list(Test.objects.filter(
                owner__groups__permissions__in=Permission.objects.all()))
        with self.assertNumQueries(0):
            data4 = list(Test.objects.filter(
                owner__groups__permissions__in=Permission.objects.all()))
        self.assertListEqual(data4, data3)
        self.assertListEqual(data4, [self.t1, self.t1, self.t1])

        with self.assertNumQueries(1):
            data5 = list(
                Test.objects.filter(
                    owner__groups__permissions__in=Permission.objects.all()
                ).distinct())
        with self.assertNumQueries(0):
            data6 = list(
                Test.objects.filter(
                    owner__groups__permissions__in=Permission.objects.all()
                ).distinct())
        self.assertListEqual(data6, data5)
        self.assertListEqual(data6, [self.t1])

    def test_aggregate(self):
        Test.objects.create(name='test3', owner=self.user)
        with self.assertNumQueries(1):
            n1 = User.objects.aggregate(n=Count('test'))['n']
        with self.assertNumQueries(0):
            n2 = User.objects.aggregate(n=Count('test'))['n']
        self.assertEqual(n2, n1)
        self.assertEqual(n2, 3)

    def test_annotate(self):
        Test.objects.create(name='test3', owner=self.user)
        with self.assertNumQueries(1):
            data1 = list(User.objects.annotate(n=Count('test')).order_by('pk')
                         .values_list('n', flat=True))
        with self.assertNumQueries(0):
            data2 = list(User.objects.annotate(n=Count('test')).order_by('pk')
                         .values_list('n', flat=True))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [2, 1])

    def test_only(self):
        with self.assertNumQueries(1):
            t1 = Test.objects.only('name').first()
            t1.name
        with self.assertNumQueries(0):
            t2 = Test.objects.only('name').first()
            t2.name
        with self.assertNumQueries(1):
            t1.public
        with self.assertNumQueries(0):
            t2.public
        self.assertEqual(t2, t1)
        self.assertEqual(t2.name, t1.name)
        self.assertEqual(t2.public, t1.public)

    def test_defer(self):
        with self.assertNumQueries(1):
            t1 = Test.objects.defer('name').first()
            t1.public
        with self.assertNumQueries(0):
            t2 = Test.objects.defer('name').first()
            t2.public
        with self.assertNumQueries(1):
            t1.name
        with self.assertNumQueries(0):
            t2.name
        self.assertEqual(t2, t1)
        self.assertEqual(t2.name, t1.name)
        self.assertEqual(t2.public, t1.public)

    def test_select_related(self):
        # Simple select_related
        with self.assertNumQueries(1):
            t1 = Test.objects.select_related('owner').get(name='test1')
            self.assertEqual(t1.owner, self.user)
        with self.assertNumQueries(0):
            t2 = Test.objects.select_related('owner').get(name='test1')
            self.assertEqual(t2.owner, self.user)
        self.assertEqual(t2, t1)
        self.assertEqual(t2, self.t1)

        # Select_related through a foreign key
        with self.assertNumQueries(1):
            t3 = Test.objects.select_related('permission__content_type')[0]
            self.assertEqual(t3.permission, self.t1.permission)
            self.assertEqual(t3.permission.content_type,
                             self.t1__permission.content_type)
        with self.assertNumQueries(0):
            t4 = Test.objects.select_related('permission__content_type')[0]
            self.assertEqual(t4.permission, self.t1.permission)
            self.assertEqual(t4.permission.content_type,
                             self.t1__permission.content_type)
        self.assertEqual(t4, t3)
        self.assertEqual(t4, self.t1)

    def test_prefetch_related(self):
        is_mysql = connection.vendor == 'mysql'

        # Simple prefetch_related
        with self.assertNumQueries(2):
            data1 = list(User.objects.prefetch_related('user_permissions'))
        with self.assertNumQueries(0):
            permissions1 = [p for u in data1 for p in u.user_permissions.all()]
        with self.assertNumQueries(1 if is_mysql else 0):
            data2 = list(User.objects.prefetch_related('user_permissions'))
            permissions2 = [p for u in data2 for p in u.user_permissions.all()]
        self.assertListEqual(permissions2, permissions1)
        self.assertListEqual(permissions2, self.user__permissions)

        # Prefetch_related through a foreign key where exactly
        # the same prefetch_related SQL request was executed before
        with self.assertNumQueries(2 if is_mysql else 1):
            data3 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__user_permissions'))
        with self.assertNumQueries(0):
            permissions3 = [p for t in data3
                            for p in t.owner.user_permissions.all()]
        with self.assertNumQueries(1 if is_mysql else 0):
            data4 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__user_permissions'))
            permissions4 = [p for t in data4
                            for p in t.owner.user_permissions.all()]
        self.assertListEqual(permissions4, permissions3)
        self.assertListEqual(permissions4, self.user__permissions)

        # Prefetch_related through a foreign key where exactly
        # the same prefetch_related SQL request was not fetched before
        with self.assertNumQueries(2):
            data5 = list(Test.objects
                         .select_related('owner')
                         .prefetch_related('owner__user_permissions')[:1])
        with self.assertNumQueries(0):
            permissions5 = [p for t in data5
                            for p in t.owner.user_permissions.all()]
        with self.assertNumQueries(1 if is_mysql else 0):
            data6 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__user_permissions')[:1])
            permissions6 = [p for t in data6
                            for p in t.owner.user_permissions.all()]
        self.assertListEqual(permissions6, permissions5)
        self.assertListEqual(permissions6, self.user__permissions)

        # Prefetch_related through a many to many
        with self.assertNumQueries(2):
            data7 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
        with self.assertNumQueries(0):
            permissions7 = [p for t in data7
                            for g in t.owner.groups.all()
                            for p in g.permissions.all()]
        with self.assertNumQueries(2 if is_mysql else 0):
            data8 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            permissions8 = [p for t in data8
                            for g in t.owner.groups.all()
                            for p in g.permissions.all()]
        self.assertListEqual(permissions8, permissions7)
        self.assertListEqual(permissions8, self.group__permissions)

    @skip(NotImplementedError)
    def test_using(self):
        pass

    @skip(NotImplementedError)
    def test_select_for_update(self):
        pass

    def test_extra_select(self):
        """
        Tests if ``QuerySet.extra(select=…)`` is not cached.
        """

        username_length_sql = """
        SELECT LENGTH(%(user_table)s.username)
        FROM %(user_table)s
        WHERE %(user_table)s.id = %(test_table)s.owner_id
        """ % {'user_table': User._meta.db_table,
               'test_table': Test._meta.db_table}

        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(
                select={'username_length': username_length_sql}))
        with self.assertNumQueries(1):
            data2 = list(Test.objects.extra(
                select={'username_length': username_length_sql}))
        self.assertListEqual(data2, data1)
        self.assertListEqual([o.username_length for o in data2],
                             [o.username_length for o in data1])
        self.assertListEqual([o.username_length for o in data2],
                             [4, 5])

    def test_extra_where(self):
        """
        Tests if ``QuerySet.extra(where=…)`` is not cached.

        The ``where`` list of a ``QuerySet.extra`` can contain subqueries,
        and since it’s unparsed pure SQL, it can’t be reliably invalidated.
        """

        sql_condition = ("owner_id IN "
                         "(SELECT id FROM auth_user WHERE username = 'admin')")
        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(where=[sql_condition]))
        with self.assertNumQueries(1):
            data2 = list(Test.objects.extra(where=[sql_condition]))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2])

    def test_extra_tables(self):
        """
        Tests if ``QuerySet.extra(tables=…)`` is cached.

        ``tables`` can only define table names, so we can reliably invalidate
        such queries.
        """

        # QUESTION: Is there a way to access extra tables data without
        #           an extra select?
        with self.assertNumQueries(1):
            list(Test.objects.extra(tables=['auth_user']))
        with self.assertNumQueries(0):
            list(Test.objects.extra(tables=['auth_user']))

    def test_extra_order_by(self):
        """
        Tests if ``QuerySet.extra(order_by=…)`` is cached.

        As far as I know, the ``order_by`` list of a ``QuerySet.extra``
        can’t select data from other tables.
        """

        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(order_by=['-cachalot_test.name']))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.extra(order_by=['-cachalot_test.name']))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2, self.t1])

    def test_raw(self):
        """
        Tests if ``Model.objects.raw`` queries are not cached.
        """

        sql = 'SELECT * FROM %s;' % Test._meta.db_table

        with self.assertNumQueries(1):
            data1 = list(Test.objects.raw(sql))
        with self.assertNumQueries(1):
            data2 = list(Test.objects.raw(sql))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1, self.t2])

    def test_cursor_execute(self):
        """
        Tests if queries executed from a DB cursor are not cached.
        """

        sql = 'SELECT * FROM %s;' % Test._meta.db_table

        with self.assertNumQueries(1):
            cursor = connection.cursor()
            cursor.execute(sql)
            data1 = list(cursor.fetchall())
            cursor.close()
        with self.assertNumQueries(1):
            cursor = connection.cursor()
            cursor.execute(sql)
            data2 = list(cursor.fetchall())
            cursor.close()
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, list(Test.objects.values_list()))


class WriteTestCase(TestCase):
    """
    Tests if every SQL request writing data is not cached and invalidates the
    implied data.
    """

    def test_create(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            t2 = Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        with self.assertNumQueries(1):
            t3 = Test.objects.create(name='test3')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data2, [t1, t2])
        self.assertListEqual(data3, [t1, t2, t3])

        with self.assertNumQueries(1):
            t3_copy = Test.objects.create(name='test3')
        self.assertNotEqual(t3_copy, t3)
        with self.assertNumQueries(1):
            data4 = list(Test.objects.all())
        self.assertListEqual(data4, [t1, t2, t3, t3_copy])

    def test_get_or_create(self):
        """
        Tests if the ``SELECT`` query of a ``QuerySet.get_or_create``
        is cached, but not the ``INSERT`` one.
        """
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        # get_or_create has to try to find the object, then create it
        # inside a transaction.
        # This triggers 4 queries: SELECT, BEGIN, UPDATE, & COMMIT
        with self.assertNumQueries(4):
            t, created = Test.objects.get_or_create(name='test')
        self.assertTrue(created)

        with self.assertNumQueries(1):
            t_clone, created = Test.objects.get_or_create(name='test')
        self.assertFalse(created)
        self.assertEqual(t_clone, t)

        with self.assertNumQueries(0):
            t_clone, created = Test.objects.get_or_create(name='test')
        self.assertFalse(created)
        self.assertEqual(t_clone, t)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [t])

    @skip(NotImplementedError)
    def test_update_or_create(self):
        pass

    def test_bulk_create(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            unsaved_tests = [Test(name='test%02d' % i) for i in range(1, 11)]
            Test.objects.bulk_create(unsaved_tests)
        self.assertEqual(Test.objects.count(), 10)

        with self.assertNumQueries(1):
            unsaved_tests = [Test(name='test%02d' % i) for i in range(1, 11)]
            Test.objects.bulk_create(unsaved_tests)
        self.assertEqual(Test.objects.count(), 20)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertEqual(len(data2), 20)
        self.assertListEqual([t.name for t in data2],
                             ['test%02d' % (i // 2) for i in range(2, 22)])

    def test_update(self):
        with self.assertNumQueries(1):
            t = Test.objects.create(name='test1')

        with self.assertNumQueries(1):
            t1 = Test.objects.get()
        with self.assertNumQueries(1):
            t.name = 'test2'
            t.save()
        with self.assertNumQueries(1):
            t2 = Test.objects.get()
        self.assertEqual(t1.name, 'test1')
        self.assertEqual(t2.name, 'test2')

        with self.assertNumQueries(1):
            Test.objects.update(name='test3')
        with self.assertNumQueries(1):
            t3 = Test.objects.get()
        self.assertEqual(t3.name, 'test3')

    def test_delete(self):
        with self.assertNumQueries(1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            t2 = Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
        with self.assertNumQueries(1):
            t2.delete()
        with self.assertNumQueries(1):
            data2 = list(Test.objects.values_list('name', flat=True))
        self.assertListEqual(data1, [t1.name, t2.name])
        self.assertListEqual(data2, [t1.name])

        with self.assertNumQueries(1):
            Test.objects.bulk_create([Test(name='test%s' % i)
                                      for i in range(2, 11)])
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 10)
        with self.assertNumQueries(1):
            Test.objects.all().delete()
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 0)

    def test_invalidate_exists(self):
        with self.assertNumQueries(1):
            self.assertFalse(Test.objects.exists())

        Test.objects.create(name='test')

        with self.assertNumQueries(1):
            self.assertTrue(Test.objects.create())

    def test_invalidate_count(self):
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 0)

        Test.objects.create(name='test1')

        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 1)

        Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 2)

    def test_invalidate_get(self):
        with self.assertNumQueries(1):
            with self.assertRaises(Test.DoesNotExist):
                Test.objects.get(name='test')

        Test.objects.create(name='test')

        with self.assertNumQueries(1):
            Test.objects.get(name='test')

        Test.objects.create(name='test')

        with self.assertNumQueries(1):
            with self.assertRaises(MultipleObjectsReturned):
                Test.objects.get(name='test')

    def test_invalidate_values(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values('name', 'public'))
        self.assertListEqual(data1, [])

        Test.objects.bulk_create([Test(name='test1'),
                                  Test(name='test2', public=True)])

        with self.assertNumQueries(1):
            data2 = list(Test.objects.values('name', 'public'))
        self.assertEqual(len(data2), 2)
        self.assertDictEqual(data2[0], {'name': 'test1', 'public': False})
        self.assertDictEqual(data2[1], {'name': 'test2', 'public': True})

        Test.objects.all()[0].delete()

        with self.assertNumQueries(1):
            data3 = list(Test.objects.values('name', 'public'))
        self.assertEqual(len(data3), 1)
        self.assertDictEqual(data3[0], {'name': 'test2', 'public': True})

    def test_invalidate_aggregate(self):
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 0)

        with self.assertNumQueries(1):
            u = User.objects.create_user('test')
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 0)

        with self.assertNumQueries(1):
            Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 0)

        with self.assertNumQueries(1):
            Test.objects.create(name='test2', owner=u)
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 1)

        with self.assertNumQueries(1):
            Test.objects.create(name='test3')
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 1)

    def test_invalidate_annotate(self):
        with self.assertNumQueries(1):
            data1 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data2, [])

        with self.assertNumQueries(2):
            user1 = User.objects.create_user('user1')
            user2 = User.objects.create_user('user2')
        with self.assertNumQueries(1):
            data3 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data3, [user1, user2])
        self.assertListEqual([u.n for u in data3], [0, 0])

        with self.assertNumQueries(1):
            Test.objects.create(name='test2', owner=user1)
        with self.assertNumQueries(1):
            data4 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data4, [user1, user2])
        self.assertListEqual([u.n for u in data4], [1, 0])

        with self.assertNumQueries(1):
            Test.objects.bulk_create([
                Test(name='test3', owner=user1),
                Test(name='test4', owner=user2),
                Test(name='test5', owner=user1),
                Test(name='test6', owner=user2),
            ])
        with self.assertNumQueries(1):
            data5 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data5, [user1, user2])
        self.assertListEqual([u.n for u in data5], [3, 2])

    def test_invalidate_subquery(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(owner__in=User.objects.all()))
        self.assertListEqual(data1, [])

        u = User.objects.create_user('test')

        with self.assertNumQueries(1):
            data2 = list(Test.objects.filter(owner__in=User.objects.all()))
        self.assertListEqual(data2, [])

        t = Test.objects.create(name='test', owner=u)

        with self.assertNumQueries(1):
            data3 = list(Test.objects.filter(owner__in=User.objects.all()))
        self.assertListEqual(data3, [t])

        with self.assertNumQueries(1):
            data4 = list(
                Test.objects.filter(
                    owner__groups__permissions__in=Permission.objects.all()
                ).distinct())
        self.assertListEqual(data4, [])

        g = Group.objects.create(name='test_group')

        with self.assertNumQueries(1):
            data5 = list(
                Test.objects.filter(
                    owner__groups__permissions__in=Permission.objects.all()
                ).distinct())
        self.assertListEqual(data5, [])

        p = Permission.objects.first()
        g.permissions.add(p)

        with self.assertNumQueries(1):
            data6 = list(
                Test.objects.filter(
                    owner__groups__permissions__in=Permission.objects.all()
                ).distinct())
        self.assertListEqual(data6, [])

        u.groups.add(g)

        with self.assertNumQueries(1):
            data7 = list(
                Test.objects.filter(
                    owner__groups__permissions__in=Permission.objects.all()
                ).distinct())
        self.assertListEqual(data7, [t])

    def test_invalidate_select_related(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.select_related('owner'))
        self.assertListEqual(data1, [])

        with self.assertNumQueries(2):
            u1 = User.objects.create_user('test1')
            u2 = User.objects.create_user('test2')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.select_related('owner'))
        self.assertListEqual(data2, [])

        with self.assertNumQueries(1):
            Test.objects.bulk_create([
                Test(name='test1', owner=u1),
                Test(name='test2', owner=u2),
                Test(name='test3', owner=u2),
                Test(name='test4', owner=u1),
            ])
        with self.assertNumQueries(1):
            data3 = list(Test.objects.select_related('owner'))
            self.assertEqual(data3[0].owner, u1)
            self.assertEqual(data3[1].owner, u2)
            self.assertEqual(data3[2].owner, u2)
            self.assertEqual(data3[3].owner, u1)

        with self.assertNumQueries(1):
            Test.objects.filter(name__in=['test1', 'test2']).delete()
        with self.assertNumQueries(1):
            data4 = list(Test.objects.select_related('owner'))
            self.assertEqual(data4[0].owner, u2)
            self.assertEqual(data4[1].owner, u1)

    def test_invalidate_prefetch_related(self):
        is_mysql = connection.vendor == 'mysql'

        with self.assertNumQueries(1):
            data1 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data2, [t1])
            self.assertEqual(data2[0].owner, None)

        with self.assertNumQueries(2):
            u = User.objects.create_user('user')
            t1.owner = u
            t1.save()
        with self.assertNumQueries(2):
            data3 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data3, [t1])
            self.assertEqual(data3[0].owner, u)
            self.assertListEqual(list(data3[0].owner.groups.all()), [])

        with self.assertNumQueries(6):
            group = Group.objects.create(name='test_group')
            permissions = list(Permission.objects.all()[:5])
            group.permissions.add(*permissions)
            u.groups.add(group)
        with self.assertNumQueries(2):
            data4 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data4, [t1])
            owner = data4[0].owner
            self.assertEqual(owner, u)
            groups = list(owner.groups.all())
            self.assertListEqual(groups, [group])
            self.assertListEqual(list(groups[0].permissions.all()),
                                 permissions)

        with self.assertNumQueries(1):
            t2 = Test.objects.create(name='test2')
        with self.assertNumQueries(3 if is_mysql else 1):
            data5 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data5, [t1, t2])
            owners = [t.owner for t in data5 if t.owner is not None]
            self.assertListEqual(owners, [u])
            groups = [g for o in owners for g in o.groups.all()]
            self.assertListEqual(groups, [group])
            data5_permissions = [p for g in groups
                                 for p in g.permissions.all()]
            self.assertListEqual(data5_permissions, permissions)

        with self.assertNumQueries(1):
            permissions[0].save()
        with self.assertNumQueries(2 if is_mysql else 1):
            list(Test.objects.select_related('owner')
                 .prefetch_related('owner__groups__permissions'))

        with self.assertNumQueries(1):
            group.name = 'modified_test_group'
            group.save()
        with self.assertNumQueries(2):
            data6 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            g = list(data6[0].owner.groups.all())[0]
            self.assertEqual(g.name, 'modified_test_group')

        with self.assertNumQueries(1):
            User.objects.update(username='modified_user')

        with self.assertNumQueries(3 if is_mysql else 2):
            data7 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertEqual(data7[0].owner.username, 'modified_user')

    @skip(NotImplementedError)
    def test_invalidate_extra_select(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_extra_where(self):
        pass

    def test_invalidate_extra_tables(self):
        with self.assertNumQueries(1):
            User.objects.create_user('user1')

        with self.assertNumQueries(1):
            data1 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data2, [t1])

        with self.assertNumQueries(1):
            t2 = Test.objects.create(name='test2')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data3, [t1, t2])

        with self.assertNumQueries(1):
            User.objects.create_user('user2')
        with self.assertNumQueries(1):
            data4 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data4, [t1, t1, t2, t2])

    @skip(NotImplementedError)
    def test_invalidate_extra_order_by(self):
        pass


class AtomicTestCase(TestCase):
    def test_successful_read_atomic(self):
        with self.assertNumQueries(3):
            with transaction.atomic():
                data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [])

    def test_unsuccessful_read_atomic(self):
        with self.assertNumQueries(3):
            try:
                with transaction.atomic():
                    data1 = list(Test.objects.all())
                    raise ZeroDivisionError
            except ZeroDivisionError:
                pass
        self.assertListEqual(data1, [])

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [])

    def test_successful_write_atomic(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(3):
            with transaction.atomic():
                t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [t1])

        with self.assertNumQueries(3):
            with transaction.atomic():
                t2 = Test.objects.create(name='test2')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1, t2])

        with self.assertNumQueries(5):
            with transaction.atomic():
                data4 = list(Test.objects.all())
                t3 = Test.objects.create(name='test3')
                t4 = Test.objects.create(name='test4')
                data5 = list(Test.objects.all())
        self.assertListEqual(data4, [t1, t2])
        self.assertListEqual(data5, [t1, t2, t3, t4])
        self.assertNotEqual(t4, t3)

    def test_unsuccessful_write_atomic(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(3):
            try:
                with transaction.atomic():
                    Test.objects.create(name='test')
                    raise ZeroDivisionError
            except ZeroDivisionError:
                pass
        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [])
        with self.assertNumQueries(1):
            with self.assertRaises(Test.DoesNotExist):
                Test.objects.get(name='test')

    def test_cache_inside_atomic(self):
        with self.assertNumQueries(3):
            with transaction.atomic():
                data1 = list(Test.objects.all())
                data2 = list(Test.objects.all())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [])

    def test_invalidation_inside_atomic(self):
        with self.assertNumQueries(5):
            with transaction.atomic():
                data1 = list(Test.objects.all())
                t = Test.objects.create(name='test')
                data2 = list(Test.objects.all())
        self.assertListEqual(data1, [])
        self.assertListEqual(data2, [t])

    def test_successful_nested_read_atomic(self):
        with self.assertNumQueries(8):
            with transaction.atomic():
                list(Test.objects.all())
                with transaction.atomic():
                    list(User.objects.all())
                    with self.assertNumQueries(2):
                        with transaction.atomic():
                            list(User.objects.all())
                with self.assertNumQueries(0):
                    list(User.objects.all())
        with self.assertNumQueries(0):
            list(Test.objects.all())
            list(User.objects.all())

    def test_unsuccessful_nested_read_atomic(self):
        with self.assertNumQueries(6):
            with transaction.atomic():
                try:
                    with transaction.atomic():
                        with self.assertNumQueries(1):
                            list(Test.objects.all())
                        raise ZeroDivisionError
                except ZeroDivisionError:
                    pass
                with self.assertNumQueries(1):
                    list(Test.objects.all())

    def test_successful_nested_write_atomic(self):
        with self.assertNumQueries(14):
            with transaction.atomic():
                t1 = Test.objects.create(name='test1')
                with transaction.atomic():
                    t2 = Test.objects.create(name='test2')
                data1 = list(Test.objects.all())
                self.assertListEqual(data1, [t1, t2])
                with transaction.atomic():
                    t3 = Test.objects.create(name='test3')
                    with transaction.atomic():
                        data2 = list(Test.objects.all())
                        self.assertListEqual(data2, [t1, t2, t3])
                        t4 = Test.objects.create(name='test4')
        data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1, t2, t3, t4])

    def test_unsuccessful_nested_write_atomic(self):
        with self.assertNumQueries(14):
            with transaction.atomic():
                t1 = Test.objects.create(name='test1')
                try:
                    with transaction.atomic():
                        t2 = Test.objects.create(name='test2')
                        data1 = list(Test.objects.all())
                        self.assertListEqual(data1, [t1, t2])
                        raise ZeroDivisionError
                except ZeroDivisionError:
                    pass
                data2 = list(Test.objects.all())
                self.assertListEqual(data2, [t1])
                try:
                    with transaction.atomic():
                        t3 = Test.objects.create(name='test3')
                        with transaction.atomic():
                            data2 = list(Test.objects.all())
                            self.assertListEqual(data2, [t1, t3])
                            raise ZeroDivisionError
                except ZeroDivisionError:
                    pass
        data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1])


class SettingsTestCase(TestCase):
    @cachalot_settings(CACHALOT_ENABLED=False)
    def test_decorator(self):
        with self.assertNumQueries(1):
            list(Test.objects.all())
        with self.assertNumQueries(1):
            list(Test.objects.all())

    def test_enabled(self):
        with cachalot_settings(CACHALOT_ENABLED=True):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(0):
                list(Test.objects.all())

        with cachalot_settings(CACHALOT_ENABLED=False):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(1):
                list(Test.objects.all())

        with self.assertNumQueries(0):
            list(Test.objects.all())

        with cachalot_settings(CACHALOT_ENABLED=False):
            with self.assertNumQueries(1):
                t = Test.objects.create(name='test')
        with self.assertNumQueries(1):
            data = list(Test.objects.all())
        self.assertListEqual(data, [t])

    @skipIf(len(settings.CACHES) == 1,
            'We can’t change the cache used since there’s only one configured')
    def test_cache(self):
        with cachalot_settings(CACHALOT_CACHE='default'):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(0):
                list(Test.objects.all())

        other_cache = [k for k in settings.CACHES if k != 'default'][0]

        with cachalot_settings(CACHALOT_CACHE=other_cache):
            with self.assertNumQueries(1):
                list(Test.objects.all())
            with self.assertNumQueries(0):
                list(Test.objects.all())


class TestThread(Thread):
    def __init__(self):
        super(TestThread, self).__init__()
        self.exit = False

    def wait_for_main(self):
        self.wait = True
        while self.wait and not self.exit:
            sleep(0.001)

    def wait_for_child(self):
        self.wait = False
        while not self.wait and not self.exit:
            sleep(0.001)

    def start(self, n=2):
        self.n = n
        super(TestThread, self).start()

    def run(self):
        for i in range(1, self.n+1):
            setattr(self, 't%d' % i, Test.objects.first())
            self.wait_for_main()

        connection.close()


class ThreadSafetyTestCase(TransactionTestCase):
    def setUp(self):
        self.thread = TestThread()

    def tearDown(self):
        if self.thread.is_alive():
            self.thread.exit = True
            self.thread.join()

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_caching(self):
        self.thread.start()
        self.thread.wait_for_child()
        t = Test.objects.create(name='test')
        self.thread.wait_for_child()

        self.assertEqual(self.thread.t1, None)
        self.assertEqual(self.thread.t2, t)

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_caching_during_atomic(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                self.thread.start()
                self.thread.wait_for_child()
                t = Test.objects.create(name='test')
                self.thread.wait_for_child()

        self.assertEqual(self.thread.t1, None)
        self.assertEqual(self.thread.t2, None)

        with self.assertNumQueries(1):
            data = Test.objects.first()
        self.assertEqual(data, t)

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_caching_before_and_during_atomic_1(self):
        self.thread.start()
        self.thread.wait_for_child()

        with self.assertNumQueries(1):
            with transaction.atomic():
                self.thread.wait_for_child()
                t = Test.objects.create(name='test')

        self.assertEqual(self.thread.t1, None)
        self.assertEqual(self.thread.t2, None)

        with self.assertNumQueries(1):
            data = Test.objects.first()
        self.assertEqual(data, t)

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_caching_before_and_during_atomic_2(self):
        self.thread.start()
        self.thread.wait_for_child()

        with self.assertNumQueries(1):
            with transaction.atomic():
                t = Test.objects.create(name='test')
                self.thread.wait_for_child()

        self.assertEqual(self.thread.t1, None)
        self.assertEqual(self.thread.t2, None)

        with self.assertNumQueries(1):
            data = Test.objects.first()
        self.assertEqual(data, t)

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_caching_during_and_after_atomic_1(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                self.thread.start()
                self.thread.wait_for_child()
                t = Test.objects.create(name='test')

        self.thread.wait_for_child()

        self.assertEqual(self.thread.t1, None)
        self.assertEqual(self.thread.t2, t)

        with self.assertNumQueries(0):
            data = Test.objects.first()
        self.assertEqual(data, t)

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_caching_during_and_after_atomic_2(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                t = Test.objects.create(name='test')
                self.thread.start()
                self.thread.wait_for_child()

        self.thread.wait_for_child()

        self.assertEqual(self.thread.t1, None)
        self.assertEqual(self.thread.t2, t)

        with self.assertNumQueries(0):
            data = Test.objects.first()
        self.assertEqual(data, t)

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_caching_during_and_after_atomic_3(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                self.thread.start(3)
                self.thread.wait_for_child()
                t = Test.objects.create(name='test')
                self.thread.wait_for_child()

        self.thread.wait_for_child()

        self.assertEqual(self.thread.t1, None)
        self.assertEqual(self.thread.t2, None)
        self.assertEqual(self.thread.t3, t)

        with self.assertNumQueries(0):
            data = Test.objects.first()
        self.assertEqual(data, t)
