# coding: utf-8

from __future__ import unicode_literals
from django.contrib.auth.models import User


try:
    from unittest import skipIf
except ImportError:  # For Python 2.6
    from unittest2 import skipIf

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.test import TransactionTestCase

from cachalot.signals import post_invalidation

from .models import Test


class SignalsTestCase(TransactionTestCase):
    def test_table_invalidated(self):
        l = []

        def receiver(sender, **kwargs):
            db_alias = kwargs['db_alias']
            l.append((sender, db_alias))

        post_invalidation.connect(receiver)
        self.assertListEqual(l, [])
        list(Test.objects.all())
        self.assertListEqual(l, [])
        Test.objects.create(name='test1')
        self.assertListEqual(l, [('cachalot_test', DEFAULT_DB_ALIAS)])
        post_invalidation.disconnect(receiver)

        del l[:]  # Empties the list
        post_invalidation.connect(receiver, sender=User._meta.db_table)
        Test.objects.create(name='test2')
        self.assertListEqual(l, [])
        User.objects.create_user('user')
        self.assertListEqual(l, [('auth_user', DEFAULT_DB_ALIAS)])

    @skipIf(len(settings.DATABASES) == 1,
            'We can’t change the DB used since there’s only one configured')
    def test_table_invalidated_multi_db(self):
        db_alias2 = next(alias for alias in settings.DATABASES
                         if alias != DEFAULT_DB_ALIAS)
        l = []

        def receiver(sender, **kwargs):
            db_alias = kwargs['db_alias']
            l.append((sender, db_alias))

        post_invalidation.connect(receiver)
        self.assertListEqual(l, [])
        Test.objects.using(DEFAULT_DB_ALIAS).create(name='test')
        self.assertListEqual(l, [('cachalot_test', DEFAULT_DB_ALIAS)])
        Test.objects.using(db_alias2).create(name='test')
        self.assertListEqual(l, [
            ('cachalot_test', DEFAULT_DB_ALIAS),
            ('cachalot_test', db_alias2)])
        post_invalidation.disconnect(receiver)
