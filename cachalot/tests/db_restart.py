"""
Test cases for cache invalidation after database restart.

This tests the scenario described in the issue where cache invalidation
doesn't occur after a database restart when data is modified outside Django.
"""
from unittest import skipIf

from django.db import connection, transaction
from django.test import TransactionTestCase

from .models import Test
from .test_utils import TestUtilsMixin, FilteredTransactionTestCase


class DatabaseRestartTestCase(TestUtilsMixin, FilteredTransactionTestCase):
    """
    Tests cache invalidation after simulated database restart scenarios.
    
    The issue: After a database restart, if data is modified outside Django
    (e.g., via direct SQL or database restore), the cache still contains
    stale data because Django-cachalot relies on Django ORM operations
    to track invalidations.
    """

    def test_cache_invalidation_after_external_update(self):
        """
        Reproduces the issue from the bug report:
        1. Set up cachalot to cache a table
        2. Make a query to that table - Check a DB query was made
        3. Make the same query - Check a DB query was not made
        4. Update a record returned by that query
        5. Make the same query - Check the new value is returned
        6. Simulate DB restart by modifying data via raw SQL
        7. Make the same query
        8. The stale value should NOT be returned (this is the bug)
        """
        # Step 1-2: Create data and cache it
        with self.assertNumQueries(1):
            Test.objects.create(name='test1', public=False)
        
        # First query - should hit DB
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(name='test1').values('name', 'public'))
        self.assertEqual(len(data1), 1)
        self.assertDictEqual(data1[0], {'name': 'test1', 'public': False})
        
        # Step 3: Same query - should be cached (0 queries)
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(name='test1').values('name', 'public'))
        self.assertDictEqual(data2[0], {'name': 'test1', 'public': False})
        
        # Step 4-5: Update via ORM and verify cache is invalidated
        with self.assertNumQueries(1):
            Test.objects.filter(name='test1').update(public=True)
        
        # Query again - should hit DB because cache was invalidated
        with self.assertNumQueries(1):
            data3 = list(Test.objects.filter(name='test1').values('name', 'public'))
        self.assertDictEqual(data3[0], {'name': 'test1', 'public': True})
        
        # Cache the result again
        with self.assertNumQueries(0):
            data4 = list(Test.objects.filter(name='test1').values('name', 'public'))
        self.assertDictEqual(data4[0], {'name': 'test1', 'public': True})
        
        # Step 6-7: Simulate DB restart scenario
        # Update data via raw SQL (simulating external DB modification)
        # This currently triggers invalidation because of CACHALOT_INVALIDATE_RAW
        # but after a real DB restart, timestamps might be out of sync
        with self.assertNumQueries(1):
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE cachalot_test SET public = %s WHERE name = %s",
                    [False, 'test1'])
        
        # Step 8: Query again - should NOT return stale data
        # With CACHALOT_INVALIDATE_RAW=True (default), this should work
        with self.assertNumQueries(1):
            data5 = list(Test.objects.filter(name='test1').values('name', 'public'))
        self.assertDictEqual(data5[0], {'name': 'test1', 'public': False})

    def test_cache_invalidation_with_atomic_block_and_connection_close(self):
        """
        Test that cache invalidation works after a connection close during an atomic block.
        
        This is the key scenario that causes the bug: if a database connection fails
        during an atomic transaction and the connection.needs_rollback access fails,
        the exit_atomic() cleanup might not happen, leaving stale AtomicCache state.
        """
        from django.db import transaction
        
        # Create and cache some data
        with self.assertNumQueries(1):
            t = Test.objects.create(name='atomic_test', public=False)
        
        # Query and cache it
        with self.assertNumQueries(1):
            data1 = list(Test.objects.filter(name='atomic_test'))
        self.assertEqual(len(data1), 1)
        self.assertEqual(data1[0].public, False)
        
        # Verify it's cached
        with self.assertNumQueries(0):
            data2 = list(Test.objects.filter(name='atomic_test'))
        self.assertEqual(data2[0].public, False)
        
        # Now simulate a DB restart during an atomic block
        # This is the critical scenario that was causing the bug
        try:
            with transaction.atomic():
                # Close the connection to simulate DB restart
                # This will cause the atomic exit to potentially fail
                connection.close()
                # Force a reconnect by making a query
                # This simulates what happens after a real DB restart
                list(Test.objects.all()[:1])
        except Exception:
            # We expect some exception due to the connection close
            pass
        
        # After the atomic block exits (even with errors), cache invalidation
        # should still work. Test that an update properly invalidates the cache.
        with self.assertNumQueries(1):
            Test.objects.filter(name='atomic_test').update(public=True)
        
        # The query should get fresh data (cache should have been invalidated)
        with self.assertNumQueries(1):
            data3 = list(Test.objects.filter(name='atomic_test'))
        self.assertEqual(data3[0].public, True)
        
        # And it should be cached now
        with self.assertNumQueries(0):
            data4 = list(Test.objects.filter(name='atomic_test'))
        self.assertEqual(data4[0].public, True)

    def test_multiple_tables_after_db_restart(self):
        """
        Test that cache invalidation works across multiple tables
        after a simulated database restart.
        """
        from django.contrib.auth.models import User
        
        # Create related data
        with self.assertNumQueries(1):
            user = User.objects.create_user('testuser')
        
        with self.assertNumQueries(1):
            Test.objects.create(name='multi_test', owner=user, public=False)
        
        # Cache a query involving both tables
        with self.assertNumQueries(1):
            data1 = list(Test.objects.select_related('owner').filter(name='multi_test'))
        self.assertEqual(len(data1), 1)
        self.assertEqual(data1[0].owner.username, 'testuser')
        self.assertEqual(data1[0].public, False)
        
        # Verify caching
        with self.assertNumQueries(0):
            data2 = list(Test.objects.select_related('owner').filter(name='multi_test'))
        
        # Modify via raw SQL (simulating DB restart + external change)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE cachalot_test SET public = %s WHERE name = %s",
                [True, 'multi_test'])
        
        # Should detect the change
        with self.assertNumQueries(1):
            data3 = list(Test.objects.select_related('owner').filter(name='multi_test'))
        self.assertEqual(data3[0].public, True)
