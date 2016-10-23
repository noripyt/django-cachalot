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
from django.db.transaction import TransactionManagementError
from django.test import (
    TransactionTestCase, skipUnlessDBFeature, override_settings)
from pytz import UTC

from ..utils import _get_table_cache_key
from .models import Test, TestChild


DJANGO_GTE_1_9 = django_version[:2] >= (1, 9)

if DJANGO_GTE_1_9:
    from django.db.models.functions import Now


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

        self.is_sqlite = connection.vendor == 'sqlite'

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

        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(
                date__gt=datetime.date(1900, 1, 1)))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(
                date__gt=datetime.date(1900, 1, 1)))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t2])

        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(
                datetime__lt=datetime.datetime(1900, 1, 1)))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(
                datetime__lt=datetime.datetime(1900, 1, 1)))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.t1])

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

    def test_random_order_by(self):
        with self.assertNumQueries(1):
            list(Test.objects.order_by('?'))
        with self.assertNumQueries(1):
            list(Test.objects.order_by('?'))

    def test_random_order_by_subquery(self):
        with self.assertNumQueries(1):
            list(Test.objects.filter(pk__in=Test.objects.order_by('?')))
        with self.assertNumQueries(1):
            list(Test.objects.filter(pk__in=Test.objects.order_by('?')))

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

    @skipIf(connection.vendor == 'mysql',
            'Time zones are not supported by MySQL.')
    @override_settings(USE_TZ=True)
    def test_datetimes_with_time_zones(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.datetimes('datetime', 'hour'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.datetimes('datetime', 'hour'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [
            datetime.datetime(1789, 7, 14, 16, tzinfo=UTC),
            datetime.datetime(1944, 6, 6, 6, tzinfo=UTC)])

    def test_foreign_key(self):
        with self.assertNumQueries(3):
            data1 = [t.owner for t in Test.objects.all()]
        with self.assertNumQueries(0):
            data2 = [t.owner for t in Test.objects.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [self.user, self.admin])

    def test_many_to_many(self):
        u = User.objects.create_user('test_user')
        ct = ContentType.objects.get_for_model(User)
        u.user_permissions.add(
            Permission.objects.create(
                name='Can discuss', content_type=ct, codename='discuss'),
            Permission.objects.create(
                name='Can touch', content_type=ct, codename='touch'),
            Permission.objects.create(
                name='Can cuddle', content_type=ct, codename='cuddle'))
        with self.assertNumQueries(1):
            data1 = [p.codename for p in u.user_permissions.all()]
        with self.assertNumQueries(0):
            data2 = [p.codename for p in u.user_permissions.all()]
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, ['cuddle', 'discuss', 'touch'])

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

        with self.assertNumQueries(1):
            data7 = list(
                TestChild.objects.exclude(permissions__isnull=True))
        with self.assertNumQueries(0):
            data8 = list(
                TestChild.objects.exclude(permissions__isnull=True))
        self.assertListEqual(data7, data8)
        self.assertListEqual(data7, [])

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
        # Simple prefetch_related
        with self.assertNumQueries(2):
            data1 = list(User.objects.prefetch_related('user_permissions'))
        with self.assertNumQueries(0):
            permissions1 = [p for u in data1 for p in u.user_permissions.all()]
        with self.assertNumQueries(0):
            data2 = list(User.objects.prefetch_related('user_permissions'))
            permissions2 = [p for u in data2 for p in u.user_permissions.all()]
        self.assertListEqual(permissions2, permissions1)
        self.assertListEqual(permissions2, self.user__permissions)

        # Prefetch_related through a foreign key where exactly
        # the same prefetch_related SQL request was executed before
        with self.assertNumQueries(1):
            data3 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__user_permissions'))
        with self.assertNumQueries(0):
            permissions3 = [p for t in data3
                            for p in t.owner.user_permissions.all()]
        with self.assertNumQueries(0):
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
        with self.assertNumQueries(0):
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
        with self.assertNumQueries(0):
            data8 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            permissions8 = [p for t in data8
                            for g in t.owner.groups.all()
                            for p in g.permissions.all()]
        self.assertListEqual(permissions8, permissions7)
        self.assertListEqual(permissions8, self.group__permissions)

    @skipUnlessDBFeature('has_select_for_update')
    def test_select_for_update(self):
        """
        Tests if ``select_for_update`` queries are not cached.
        """
        with self.assertRaises(TransactionManagementError):
            list(Test.objects.select_for_update())

        with self.assertNumQueries(1):
            with transaction.atomic():
                data1 = list(Test.objects.select_for_update())
                self.assertListEqual(data1, [self.t1, self.t2])
                self.assertListEqual([t.name for t in data1],
                                     ['test1', 'test2'])

        with self.assertNumQueries(1):
            with transaction.atomic():
                data2 = list(Test.objects.select_for_update())
                self.assertListEqual(data2, [self.t1, self.t2])
                self.assertListEqual([t.name for t in data2],
                                     ['test1', 'test2'])

        with self.assertNumQueries(2):
            with transaction.atomic():
                data3 = list(Test.objects.select_for_update())
                data4 = list(Test.objects.select_for_update())
                self.assertListEqual(data3, [self.t1, self.t2])
                self.assertListEqual(data4, [self.t1, self.t2])
                self.assertListEqual([t.name for t in data3],
                                     ['test1', 'test2'])
                self.assertListEqual([t.name for t in data4],
                                     ['test1', 'test2'])

    def test_having(self):
        with self.assertNumQueries(1):
            data1 = list(User.objects.annotate(n=Count('user_permissions'))
                         .filter(n__gte=1))
            self.assertListEqual(data1, [self.user])

        with self.assertNumQueries(0):
            data2 = list(User.objects.annotate(n=Count('user_permissions'))
                         .filter(n__gte=1))
            self.assertListEqual(data2, [self.user])

        with self.assertNumQueries(1):
            self.assertEqual(User.objects.annotate(n=Count('user_permissions'))
                             .filter(n__gte=1).count(), 1)

        with self.assertNumQueries(0):
            self.assertEqual(User.objects.annotate(n=Count('user_permissions'))
                             .filter(n__gte=1).count(), 1)

    def test_extra_select(self):
        username_length_sql = """
        SELECT LENGTH(%(user_table)s.username)
        FROM %(user_table)s
        WHERE %(user_table)s.id = %(test_table)s.owner_id
        """ % {'user_table': User._meta.db_table,
               'test_table': Test._meta.db_table}

        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(
                select={'username_length': username_length_sql}))
            self.assertListEqual(data1, [self.t1, self.t2])
            self.assertListEqual([o.username_length for o in data1], [4, 5])
        with self.assertNumQueries(0):
            data2 = list(Test.objects.extra(
                select={'username_length': username_length_sql}))
            self.assertListEqual(data2, [self.t1, self.t2])
            self.assertListEqual([o.username_length for o in data2], [4, 5])

    def test_extra_where(self):
        sql_condition = ("owner_id IN "
                         "(SELECT id FROM auth_user WHERE username = 'admin')")
        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(where=[sql_condition]))
            self.assertListEqual(data1, [self.t2])
        with self.assertNumQueries(0):
            data2 = list(Test.objects.extra(where=[sql_condition]))
            self.assertListEqual(data2, [self.t2])

    def test_extra_tables(self):
        with self.assertNumQueries(1):
            list(Test.objects.extra(tables=['auth_user']))
        with self.assertNumQueries(0):
            list(Test.objects.extra(tables=['auth_user']))

    def test_extra_order_by(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.extra(order_by=['-cachalot_test.name']))
            self.assertListEqual(data1, [self.t2, self.t1])
        with self.assertNumQueries(0):
            data2 = list(Test.objects.extra(order_by=['-cachalot_test.name']))
            self.assertListEqual(data2, [self.t2, self.t1])

    def test_table_inheritance(self):
        with self.assertNumQueries(3 if self.is_sqlite else 2):
            t_child = TestChild.objects.create(name='test_child')

        with self.assertNumQueries(1):
            self.assertEqual(TestChild.objects.get(), t_child)

        with self.assertNumQueries(0):
            self.assertEqual(TestChild.objects.get(), t_child)

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

    def test_cursor_execute_unicode(self):
        """
        Tests if queries executed from a DB cursor are not cached.
        """

        attname_column_list = [f.get_attname_column()
                               for f in Test._meta.fields]
        attnames = [t[0] for t in attname_column_list]
        columns = [t[1] for t in attname_column_list]
        sql = "SELECT CAST('é' AS CHAR), %s FROM %s;" % (', '.join(columns),
                                                         Test._meta.db_table)

        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute(sql)
                data1 = list(cursor.fetchall())
        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute(sql)
                data2 = list(cursor.fetchall())
        self.assertListEqual(data2, data1)
        self.assertListEqual(
            data2,
            [('é',) + l for l in Test.objects.values_list(*attnames)])

    @skipIf(connection.vendor == 'sqlite',
            'SQLite doesn’t accept bytes as raw query.')
    def test_cursor_execute_bytes(self):
        attname_column_list = [f.get_attname_column()
                               for f in Test._meta.fields]
        attnames = [t[0] for t in attname_column_list]
        columns = [t[1] for t in attname_column_list]
        sql = "SELECT CAST('é' AS CHAR), %s FROM %s;" % (', '.join(columns),
                                                         Test._meta.db_table)
        sql = sql.encode('utf-8')

        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute(sql)
                data1 = list(cursor.fetchall())
        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute(sql)
                data2 = list(cursor.fetchall())
        self.assertListEqual(data2, data1)
        self.assertListEqual(
            data2,
            [('é',) + l for l in Test.objects.values_list(*attnames)])

    def test_missing_table_cache_key(self):
        with self.assertNumQueries(1):
            list(Test.objects.all())
        with self.assertNumQueries(0):
            list(Test.objects.all())

        table_cache_key = _get_table_cache_key(connection.alias,
                                               Test._meta.db_table)
        cache.delete(table_cache_key)

        with self.assertNumQueries(1):
            list(Test.objects.all())

    def test_unicode_get(self):
        with self.assertNumQueries(1):
            with self.assertRaises(Test.DoesNotExist):
                Test.objects.get(name='Clémentine')
        with self.assertNumQueries(0):
            with self.assertRaises(Test.DoesNotExist):
                Test.objects.get(name='Clémentine')

    def test_unicode_table_name(self):
        """
        Tests if using unicode in table names does not break caching.
        """
        table_name = 'Clémentine'
        if connection.vendor == 'postgresql':
            table_name = '"%s"' % table_name
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE %s (taste VARCHAR(20));' % table_name)
        with self.assertNumQueries(1):
            list(Test.objects.extra(tables=['Clémentine']))
        with self.assertNumQueries(0):
            list(Test.objects.extra(tables=['Clémentine']))
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE %s;' % table_name)


class ParameterTypeTestCase(TransactionTestCase):
    def setUp(self):
        self.is_sqlite = connection.vendor == 'sqlite'
        self.is_mysql = connection.vendor == 'mysql'
        if self.is_mysql:
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

    def test_unknown_parameter_type(self):
        """
        Tests if queries with an unknown parameter type are not cached.

        We don’t cache parameters with an unknown type because we don’t know
        how to hash them.

        Here we use a binary field, as it uses special parameters
        on PostgreSQL and SQLite (but not on MySQL).
        A similar result would be obtained using a geographic field, but it’s
        more complex to test, since geographic database backends have a few
        side effects, such as changing the number of queries
        of a bulk_create of n objects from 1 to n.
        """

        with self.assertNumQueries(1):
            list(Test.objects.filter(bin=None))
        with self.assertNumQueries(0):
            list(Test.objects.filter(bin=None))

        with self.assertNumQueries(1):
            list(Test.objects.filter(bin=b'abc'))
        with self.assertNumQueries(0 if self.is_mysql else 1):
            list(Test.objects.filter(bin=b'abc'))

        with self.assertNumQueries(1):
            list(Test.objects.filter(bin=b'def'))
        with self.assertNumQueries(0 if self.is_mysql else 1):
            list(Test.objects.filter(bin=b'def'))

    def test_float(self):
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test1', a_float=0.123456789)
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test2', a_float=12345.6789)
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('a_float', flat=True).filter(
                a_float__isnull=False).order_by('a_float'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('a_float', flat=True).filter(
                a_float__isnull=False).order_by('a_float'))
        self.assertListEqual(data2, data1)
        self.assertEqual(len(data2), 2)
        self.assertAlmostEqual(data2[0], 0.123456789, delta=0.0001)
        self.assertAlmostEqual(data2[1], 12345.6789, delta=0.0001)

        with self.assertNumQueries(1):
            Test.objects.get(a_float=0.123456789)
        with self.assertNumQueries(0):
            Test.objects.get(a_float=0.123456789)

    def test_decimal(self):
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test1', a_decimal=Decimal('123.45'))
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test1', a_decimal=Decimal('12.3'))
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('a_decimal', flat=True).filter(
                a_decimal__isnull=False).order_by('a_decimal'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('a_decimal', flat=True).filter(
                a_decimal__isnull=False).order_by('a_decimal'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [Decimal('12.3'), Decimal('123.45')])

        with self.assertNumQueries(1):
            Test.objects.get(a_decimal=Decimal('123.45'))
        with self.assertNumQueries(0):
            Test.objects.get(a_decimal=Decimal('123.45'))

    def test_ipv4_address(self):
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test1', ip='127.0.0.1')
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test2', ip='192.168.0.1')
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('ip', flat=True).filter(
                ip__isnull=False).order_by('ip'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('ip', flat=True).filter(
                ip__isnull=False).order_by('ip'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, ['127.0.0.1', '192.168.0.1'])

        with self.assertNumQueries(1):
            Test.objects.get(ip='127.0.0.1')
        with self.assertNumQueries(0):
            Test.objects.get(ip='127.0.0.1')

    def test_ipv6_address(self):
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test1', ip='2001:db8:a0b:12f0::1/64')
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test2', ip='2001:db8:0:85a3::ac1f:8001')
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('ip', flat=True).filter(
                ip__isnull=False).order_by('ip'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list('ip', flat=True).filter(
                ip__isnull=False).order_by('ip'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [
            '2001:db8:0:85a3::ac1f:8001', '2001:db8:a0b:12f0::1/64'])

        with self.assertNumQueries(1):
            Test.objects.get(ip='2001:db8:0:85a3::ac1f:8001')
        with self.assertNumQueries(0):
            Test.objects.get(ip='2001:db8:0:85a3::ac1f:8001')

    def test_duration(self):
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test1', duration=datetime.timedelta(30))
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test2', duration=datetime.timedelta(60))
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list(
                'duration', flat=True).filter(
                duration__isnull=False).order_by('duration'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list(
                'duration', flat=True).filter(
                duration__isnull=False).order_by('duration'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [
            datetime.timedelta(30), datetime.timedelta(60)])

        with self.assertNumQueries(1):
            Test.objects.get(duration=datetime.timedelta(30))
        with self.assertNumQueries(0):
            Test.objects.get(duration=datetime.timedelta(30))

    def test_uuid(self):
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test1',
                                uuid='1cc401b7-09f4-4520-b8d0-c267576d196b')
        with self.assertNumQueries(2 if self.is_sqlite else 1):
            Test.objects.create(name='test2',
                                uuid='ebb3b6e1-1737-4321-93e3-4c35d61ff491')
        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list(
                'uuid', flat=True).filter(
                uuid__isnull=False).order_by('uuid'))
        with self.assertNumQueries(0):
            data2 = list(Test.objects.values_list(
                'uuid', flat=True).filter(
                uuid__isnull=False).order_by('uuid'))
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [
            UUID('1cc401b7-09f4-4520-b8d0-c267576d196b'),
            UUID('ebb3b6e1-1737-4321-93e3-4c35d61ff491')])

        with self.assertNumQueries(1):
            Test.objects.get(uuid=UUID('1cc401b7-09f4-4520-b8d0-c267576d196b'))
        with self.assertNumQueries(0):
            Test.objects.get(uuid=UUID('1cc401b7-09f4-4520-b8d0-c267576d196b'))

    @skipUnless(DJANGO_GTE_1_9, 'Now is only available on Django >= 1.9')
    def test_now(self):
        """
        Checks that queries with a Now() parameter are not cached.
        """
        obj = Test.objects.create(datetime='1992-07-02T12:00:00')
        qs = Test.objects.filter(
            datetime__lte=Now())
        with self.assertNumQueries(1):
            obj1 = qs.get()
        with self.assertNumQueries(1):
            obj2 = qs.get()
        self.assertEqual(obj1, obj2)
        self.assertEqual(obj1, obj)
