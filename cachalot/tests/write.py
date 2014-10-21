# coding: utf-8

from __future__ import unicode_literals
try:
    from unittest import skip, skipIf
except ImportError:  # For Python 2.6
    from unittest2 import skip, skipIf

from django import VERSION as django_version
from django.contrib.auth.models import User, Permission, Group
from django.core.exceptions import MultipleObjectsReturned
from django.core.management import call_command
from django.db import connection, transaction
from django.db.models import Count
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Test


class WriteTestCase(TransactionTestCase):
    """
    Tests if every SQL request writing data is not cached and invalidates the
    implied data.
    """

    def test_create(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(2 if is_sqlite else 1):
            t2 = Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        with self.assertNumQueries(2 if is_sqlite else 1):
            t3 = Test.objects.create(name='test3')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data2, [t1, t2])
        self.assertListEqual(data3, [t1, t2, t3])

        with self.assertNumQueries(2 if is_sqlite else 1):
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

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(3 if is_sqlite else 2):
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

    @skipIf(django_version < (1, 7),
            'QuerySet.update_or_create is not implemented in Django < 1.7')
    def test_update_or_create(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [])

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(3 if is_sqlite else 2):
            t, created = Test.objects.update_or_create(
                name='test', defaults={'public': True})
            self.assertTrue(created)
            self.assertEqual(t.name, 'test')
            self.assertEqual(t.public, True)

        with self.assertNumQueries(3 if is_sqlite else 2):
            t, created = Test.objects.update_or_create(
                name='test', defaults={'public': False})
            self.assertFalse(created)
            self.assertEqual(t.name, 'test')
            self.assertEqual(t.public, False)

        # The number of SQL queries doesn’t decrease because update_or_create
        # always calls an UPDATE, even when data wasn’t changed.
        with self.assertNumQueries(3 if is_sqlite else 2):
            t, created = Test.objects.update_or_create(
                name='test', defaults={'public': False})
            self.assertFalse(created)
            self.assertEqual(t.name, 'test')
            self.assertEqual(t.public, False)

        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [t])

    def test_bulk_create(self):
        with self.assertNumQueries(1):
            data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            unsaved_tests = [Test(name='test%02d' % i) for i in range(1, 11)]
            Test.objects.bulk_create(unsaved_tests)
        self.assertEqual(Test.objects.count(), 10)

        with self.assertNumQueries(2 if is_sqlite else 1):
            unsaved_tests = [Test(name='test%02d' % i) for i in range(1, 11)]
            Test.objects.bulk_create(unsaved_tests)
        self.assertEqual(Test.objects.count(), 20)

        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertEqual(len(data2), 20)
        self.assertListEqual([t.name for t in data2],
                             ['test%02d' % (i // 2) for i in range(2, 22)])

    def test_update(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            t = Test.objects.create(name='test1')

        with self.assertNumQueries(1):
            t1 = Test.objects.get()
        with self.assertNumQueries(2 if is_sqlite else 1):
            t.name = 'test2'
            t.save()
        with self.assertNumQueries(1):
            t2 = Test.objects.get()
        self.assertEqual(t1.name, 'test1')
        self.assertEqual(t2.name, 'test2')

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.update(name='test3')
        with self.assertNumQueries(1):
            t3 = Test.objects.get()
        self.assertEqual(t3.name, 'test3')

    def test_delete(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(2 if is_sqlite else 1):
            t2 = Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            data1 = list(Test.objects.values_list('name', flat=True))
        with self.assertNumQueries(2 if is_sqlite else 1):
            t2.delete()
        with self.assertNumQueries(1):
            data2 = list(Test.objects.values_list('name', flat=True))
        self.assertListEqual(data1, [t1.name, t2.name])
        self.assertListEqual(data2, [t1.name])

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.bulk_create([Test(name='test%s' % i)
                                      for i in range(2, 11)])
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 10)
        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.all().delete()
        with self.assertNumQueries(1):
            self.assertEqual(Test.objects.count(), 0)

    def test_invalidate_exists(self):
        with self.assertNumQueries(1):
            self.assertFalse(Test.objects.exists())

        Test.objects.create(name='test')

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
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

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            u = User.objects.create_user('test')
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 0)

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 0)

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.create(name='test2', owner=u)
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 1)

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.create(name='test3')
        with self.assertNumQueries(1):
            self.assertEqual(User.objects.aggregate(n=Count('test'))['n'], 1)

    def test_invalidate_annotate(self):
        with self.assertNumQueries(1):
            data1 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data1, [])

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data2, [])

        with self.assertNumQueries(4 if is_sqlite else 2):
            user1 = User.objects.create_user('user1')
            user2 = User.objects.create_user('user2')
        with self.assertNumQueries(1):
            data3 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data3, [user1, user2])
        self.assertListEqual([u.n for u in data3], [0, 0])

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.create(name='test2', owner=user1)
        with self.assertNumQueries(1):
            data4 = list(User.objects.annotate(n=Count('test')).order_by('pk'))
        self.assertListEqual(data4, [user1, user2])
        self.assertListEqual([u.n for u in data4], [1, 0])

        with self.assertNumQueries(2 if is_sqlite else 1):
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

        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(4 if is_sqlite else 2):
            u1 = User.objects.create_user('test1')
            u2 = User.objects.create_user('test2')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.select_related('owner'))
        self.assertListEqual(data2, [])

        with self.assertNumQueries(2 if is_sqlite else 1):
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

        with self.assertNumQueries(2 if is_sqlite else 1):
            Test.objects.filter(name__in=['test1', 'test2']).delete()
        with self.assertNumQueries(1):
            data4 = list(Test.objects.select_related('owner'))
            self.assertEqual(data4[0].owner, u2)
            self.assertEqual(data4[1].owner, u1)

    def test_invalidate_prefetch_related(self):
        is_sqlite = connection.vendor == 'sqlite'
        is_mysql = connection.vendor == 'mysql'

        with self.assertNumQueries(1):
            data1 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data1, [])

        with self.assertNumQueries(2 if is_sqlite else 1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data2, [t1])
            self.assertEqual(data2[0].owner, None)

        with self.assertNumQueries(4 if is_sqlite else 2):
            u = User.objects.create_user('user')
            t1.owner = u
            t1.save()
        with self.assertNumQueries(2):
            data3 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertListEqual(data3, [t1])
            self.assertEqual(data3[0].owner, u)
            self.assertListEqual(list(data3[0].owner.groups.all()), [])

        with self.assertNumQueries(9 if is_sqlite else 6):
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

        with self.assertNumQueries(2 if is_sqlite else 1):
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

        with self.assertNumQueries(2 if is_sqlite else 1):
            permissions[0].save()
        with self.assertNumQueries(2 if is_mysql else 1):
            list(Test.objects.select_related('owner')
                 .prefetch_related('owner__groups__permissions'))

        with self.assertNumQueries(2 if is_sqlite else 1):
            group.name = 'modified_test_group'
            group.save()
        with self.assertNumQueries(2):
            data6 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            g = list(data6[0].owner.groups.all())[0]
            self.assertEqual(g.name, 'modified_test_group')

        with self.assertNumQueries(2 if is_sqlite else 1):
            User.objects.update(username='modified_user')

        with self.assertNumQueries(3 if is_mysql else 2):
            data7 = list(Test.objects.select_related('owner')
                         .prefetch_related('owner__groups__permissions'))
            self.assertEqual(data7[0].owner.username, 'modified_user')

    @skipUnlessDBFeature('has_select_for_update')
    def test_invalidate_select_for_update(self):
        with self.assertNumQueries(1):
            Test.objects.bulk_create([Test(name='test1'), Test(name='test2')])

        with self.assertNumQueries(1):
            with transaction.atomic():
                data1 = list(Test.objects.select_for_update())
                self.assertListEqual([t.name for t in data1],
                                     ['test1', 'test2'])

        with self.assertNumQueries(1):
            with transaction.atomic():
                qs = Test.objects.select_for_update()
                qs.update(name='test3')

        with self.assertNumQueries(1):
            with transaction.atomic():
                data2 = list(Test.objects.select_for_update())
                self.assertListEqual([t.name for t in data2], ['test3'] * 2)

    @skip(NotImplementedError)
    def test_invalidate_extra_select(self):
        pass

    @skip(NotImplementedError)
    def test_invalidate_extra_where(self):
        pass

    def test_invalidate_extra_tables(self):
        is_sqlite = connection.vendor == 'sqlite'

        with self.assertNumQueries(2 if is_sqlite else 1):
            User.objects.create_user('user1')

        with self.assertNumQueries(1):
            data1 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data1, [])

        with self.assertNumQueries(2 if is_sqlite else 1):
            t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data2, [t1])

        with self.assertNumQueries(2 if is_sqlite else 1):
            t2 = Test.objects.create(name='test2')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data3, [t1, t2])

        with self.assertNumQueries(2 if is_sqlite else 1):
            User.objects.create_user('user2')
        with self.assertNumQueries(1):
            data4 = list(Test.objects.all().extra(tables=['auth_user']))
        self.assertListEqual(data4, [t1, t1, t2, t2])

    @skip(NotImplementedError)
    def test_invalidate_extra_order_by(self):
        pass


class DatabaseCommandTestCase(TransactionTestCase):
    def setUp(self):
        self.t = Test.objects.create(name='test1')

    def test_flush(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t])

        call_command('flush', verbosity=0, interactive=False)

        if django_version >= (1, 7) and connection.vendor == 'mysql':
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [])

    def test_loaddata(self):
        with self.assertNumQueries(1):
            self.assertListEqual(list(Test.objects.all()), [self.t])

        call_command('loaddata', 'cachalot/tests/loaddata_fixture.json',
                     verbosity=0, interactive=False)

        if django_version >= (1, 7) and connection.vendor == 'mysql':
            # We need to reopen the connection or Django
            # will execute an extra SQL request below.
            connection.cursor()

        with self.assertNumQueries(1):
            self.assertListEqual([t.name for t in Test.objects.all()],
                                 ['test1', 'test2'])
