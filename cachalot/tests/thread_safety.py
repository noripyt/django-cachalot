# coding: utf-8

from __future__ import unicode_literals
from threading import Thread, Event

from django.db import connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Test


class TestThread(Thread):
    def __init__(self):
        super(TestThread, self).__init__()
        self.event0 = Event()
        self.event1 = Event()

    def wait_for_main(self):
        self.event1.set()
        self.event1.clear()
        self.event0.wait(0.5)

    def wait_for_child(self):
        self.event0.set()
        self.event0.clear()
        self.event1.wait(0.5)

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
