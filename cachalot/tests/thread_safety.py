import sys
import threading
from threading import Barrier, Thread

from django.db import connection, transaction
from django.db.backends.utils import CursorWrapper
from django.db.transaction import Atomic
from django.test import SimpleTestCase, skipUnlessDBFeature

from ..monkey_patch import WRITE_COMPILERS, SQLCompiler
from ..settings import cachalot_settings
from .models import Test
from .test_utils import TestUtilsMixin, FilteredTransactionTestCase


class TestThread(Thread):
    def start_and_join(self):
        self.start()
        self.join()
        return self.t

    def run(self):
        self.t = Test.objects.first()
        connection.close()


@skipUnlessDBFeature('test_db_allows_multiple_connections')
class ThreadSafetyTestCase(TestUtilsMixin, FilteredTransactionTestCase):
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


class SettingsReloadThreadSafetyTestCase(SimpleTestCase):
    """Concurrent ``cachalot_settings.reload()`` calls must not corrupt
    the monkey-patches.

    ``CachalotPanel`` triggers a reload on every debug toolbar request,
    so two simultaneous requests race in ``Settings.unload``: both see
    ``patched == True`` and both unpatch, the second failing with
    ``AttributeError: 'function' object has no attribute '__wrapped__'``.
    """

    def setUp(self):
        self.saved_patches = (
            CursorWrapper.execute, CursorWrapper.executemany,
            Atomic.__enter__, Atomic.__exit__,
            SQLCompiler.execute_sql,
            [compiler.execute_sql for compiler in WRITE_COMPILERS],
            cachalot_settings.patched,
        )
        self.thread_exceptions = []
        self.saved_excepthook = threading.excepthook
        threading.excepthook = \
            lambda args: self.thread_exceptions.append(args.exc_value)
        self.saved_switch_interval = sys.getswitchinterval()
        # Forces frequent thread switches to reliably trigger the race.
        sys.setswitchinterval(1e-6)

    def tearDown(self):
        sys.setswitchinterval(self.saved_switch_interval)
        threading.excepthook = self.saved_excepthook
        (CursorWrapper.execute, CursorWrapper.executemany,
         Atomic.__enter__, Atomic.__exit__,
         SQLCompiler.execute_sql,
         write_execute_sqls, cachalot_settings.patched) = self.saved_patches
        for compiler, execute_sql in zip(WRITE_COMPILERS,
                                         write_execute_sqls):
            compiler.execute_sql = execute_sql

    def test_concurrent_reload(self):
        barrier = Barrier(4)

        def reload_repeatedly():
            barrier.wait()
            for _ in range(250):
                cachalot_settings.reload()

        threads = [Thread(target=reload_repeatedly) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(self.thread_exceptions, [])
        self.assertTrue(cachalot_settings.patched)
        self.assertTrue(hasattr(Atomic.__enter__, '__wrapped__'))
        self.assertFalse(
            hasattr(Atomic.__enter__.__wrapped__, '__wrapped__'),
            'Atomic.__enter__ was patched more than once.')
