from threading import Thread

from django.db import connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Test
from .test_utils import TestUtilsMixin


class TestThread(Thread):
    def start_and_join(self):
        self.start()
        self.join()
        return self.t

    def run(self):
        self.t = Test.objects.first()
        connection.close()


@skipUnlessDBFeature('test_db_allows_multiple_connections')
class ThreadSafetyTestCase(TestUtilsMixin, TransactionTestCase):
    def test_concurrent_caching(self):
        t1 = TestThread().start_and_join()
        t = Test.objects.create(name='test')
        t2 = TestThread().start_and_join()

        self.assertEqual(t1, None)
        self.assertEqual(t2, t)

    def test_concurrent_caching_during_atomic(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                t1 = TestThread().start_and_join()
                t = Test.objects.create(name='test')
                t2 = TestThread().start_and_join()

        self.assertEqual(t1, None)
        self.assertEqual(t2, None)

        with self.assertNumQueries(1):
            data = Test.objects.first()
        self.assertEqual(data, t)

    def test_concurrent_caching_before_and_during_atomic_1(self):
        t1 = TestThread().start_and_join()

        with self.assertNumQueries(1):
            with transaction.atomic():
                t2 = TestThread().start_and_join()
                t = Test.objects.create(name='test')

        self.assertEqual(t1, None)
        self.assertEqual(t2, None)

        with self.assertNumQueries(1):
            data = Test.objects.first()
        self.assertEqual(data, t)

    def test_concurrent_caching_before_and_during_atomic_2(self):
        t1 = TestThread().start_and_join()

        with self.assertNumQueries(1):
            with transaction.atomic():
                t = Test.objects.create(name='test')
                t2 = TestThread().start_and_join()

        self.assertEqual(t1, None)
        self.assertEqual(t2, None)

        with self.assertNumQueries(1):
            data = Test.objects.first()
        self.assertEqual(data, t)

    def test_concurrent_caching_during_and_after_atomic_1(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                t1 = TestThread().start_and_join()
                t = Test.objects.create(name='test')

        t2 = TestThread().start_and_join()

        self.assertEqual(t1, None)
        self.assertEqual(t2, t)

        with self.assertNumQueries(0):
            data = Test.objects.first()
        self.assertEqual(data, t)

    def test_concurrent_caching_during_and_after_atomic_2(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                t = Test.objects.create(name='test')
                t1 = TestThread().start_and_join()

        t2 = TestThread().start_and_join()

        self.assertEqual(t1, None)
        self.assertEqual(t2, t)

        with self.assertNumQueries(0):
            data = Test.objects.first()
        self.assertEqual(data, t)

    def test_concurrent_caching_during_and_after_atomic_3(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                t1 = TestThread().start_and_join()
                t = Test.objects.create(name='test')
                t2 = TestThread().start_and_join()

        t3 = TestThread().start_and_join()

        self.assertEqual(t1, None)
        self.assertEqual(t2, None)
        self.assertEqual(t3, t)

        with self.assertNumQueries(0):
            data = Test.objects.first()
        self.assertEqual(data, t)
