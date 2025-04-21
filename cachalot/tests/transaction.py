from cachalot.transaction import AtomicCache

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction, connection, IntegrityError
from django.test import SimpleTestCase, skipUnlessDBFeature

from .models import Test
from .test_utils import TestUtilsMixin, FilteredTransactionTestCase


class AtomicTestCase(TestUtilsMixin, FilteredTransactionTestCase):
    def test_successful_read_atomic(self):
        with self.assertNumQueries(1):
            with transaction.atomic():
                data1 = list(Test.objects.all())
        self.assertListEqual(data1, [])

        with self.assertNumQueries(0):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [])

    def test_unsuccessful_read_atomic(self):
        with self.assertNumQueries(1):
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

        with self.assertNumQueries(1):
            with transaction.atomic():
                t1 = Test.objects.create(name='test1')
        with self.assertNumQueries(1):
            data2 = list(Test.objects.all())
        self.assertListEqual(data2, [t1])

        with self.assertNumQueries(1):
            with transaction.atomic():
                t2 = Test.objects.create(name='test2')
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1, t2])

        with self.assertNumQueries(3):
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

        with self.assertNumQueries(1):
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
        with self.assertNumQueries(1):
            with transaction.atomic():
                data1 = list(Test.objects.all())
                data2 = list(Test.objects.all())
        self.assertListEqual(data2, data1)
        self.assertListEqual(data2, [])

    def test_invalidation_inside_atomic(self):
        with self.assertNumQueries(3):
            with transaction.atomic():
                data1 = list(Test.objects.all())
                t = Test.objects.create(name='test')
                data2 = list(Test.objects.all())
        self.assertListEqual(data1, [])
        self.assertListEqual(data2, [t])

    def test_successful_nested_read_atomic(self):
        with self.assertNumQueries(6):
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
        with self.assertNumQueries(5):
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
        with self.assertNumQueries(12):
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
        with self.assertNumQueries(15):
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
        with self.assertNumQueries(1):
            data3 = list(Test.objects.all())
        self.assertListEqual(data3, [t1])
    
    @skipUnlessDBFeature('can_defer_constraint_checks')
    def test_deferred_error(self):
        """
        Checks that an error occurring during the end of a transaction
        has no impact on future queries.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                'CREATE TABLE example ('
                'id int UNIQUE DEFERRABLE INITIALLY DEFERRED);')
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    with self.assertNumQueries(1):
                        list(Test.objects.all())
                    cursor.execute(
                        'INSERT INTO example VALUES (1), (1);'
                        '-- ' + Test._meta.db_table)  # Should invalidate Test.
        with self.assertNumQueries(1):
            list(Test.objects.all())


class AtomicCacheTestCase(SimpleTestCase):
    def setUp(self):
        self.atomic_cache = AtomicCache(cache, 'db_alias')
    
    def test_set(self):
        self.assertDictEqual(self.atomic_cache, {})
        self.atomic_cache.set('key', 'value', None)
        self.assertDictEqual(self.atomic_cache, {'key': 'value'})
        
    def test_get_many(self):
        """Test basic get_many functionality"""
        # Setup mock parent cache
        class MockCache:
            def __init__(self):
                self.data = {}
            
            def get_many(self, keys):
                return {k: self.data[k] for k in keys if k in self.data}
            
            def set(self, key, value, timeout=None):
                self.data[key] = value
        
        parent_cache = MockCache()
        parent_cache.set('parent_key', 'parent_value')
        
        # Setup atomic cache with values
        atomic_cache = AtomicCache(parent_cache, 'db_alias')
        atomic_cache.set('local_key', 'local_value', None)
        
        # Test get_many retrieves from both caches
        result = atomic_cache.get_many(['local_key', 'parent_key', 'missing_key'])
        
        self.assertEqual(result['local_key'], 'local_value')
        self.assertEqual(result['parent_key'], 'parent_value')
        self.assertNotIn('missing_key', result)

    def test_nested_atomic_caches(self):
        """
        Test that nested AtomicCache instances don't cause recursion errors.
        This simulates the scenario that was causing the RecursionError in issue #262.
        """
        # Create a base cache
        class MockBaseCache:
            def __init__(self):
                self.data = {}
            
            def get_many(self, keys):
                result = {}
                for k in keys:
                    result[k] = self.data.get(k, f'base_value_{k}')
                return result
            
            def set(self, key, value, timeout=None):
                self.data[key] = value
        
        base_cache = MockBaseCache()
        
        # Create a nested chain of AtomicCache instances (simulating middleware wrapping)
        cache_level_1 = AtomicCache(base_cache, 'db1')
        cache_level_2 = AtomicCache(cache_level_1, 'db2')
        cache_level_3 = AtomicCache(cache_level_2, 'db3')
        
        # Set some values at different levels
        cache_level_1.set('key1', 'value1', None)
        cache_level_2.set('key2', 'value2', None)
        
        # Test get_many traverses the chain without recursion
        result = cache_level_3.get_many(['key1', 'key2', 'key3'])
        
        # Verify results - key1 from level_1, key2 from level_2, key3 from base
        self.assertEqual(result['key1'], 'value1')
        self.assertEqual(result['key2'], 'value2')
        self.assertEqual(result['key3'], 'base_value_key3')

    def test_circular_reference(self):
        """
        Test that AtomicCache handles circular references correctly.
        This verifies that the fix prevents infinite recursion with cyclic cache chains.
        """
        # Create a mock base cache
        class MockBaseCache:
            def __init__(self):
                self.data = {}
            
            def get_many(self, keys):
                return {k: self.data.get(k, f'base_value_{k}') for k in keys}
            
            def set(self, key, value, timeout=None):
                self.data[key] = value
        
        base_cache = MockBaseCache()
        
        # Create atomic caches
        cache1 = AtomicCache(base_cache, 'db1')
        cache2 = AtomicCache(cache1, 'db2')
        
        # Create a circular reference (would cause recursion without the fix)
        cache1.parent_cache = cache2
        
        # Add some values
        cache1.set('key1', 'value1', None)
        cache2.set('key2', 'value2', None)
        
        # This should not cause infinite recursion
        result = cache2.get_many(['key1', 'key2', 'key3'])
        
        # We should get the values from the dictionaries directly
        self.assertEqual(result['key1'], 'value1')
        self.assertEqual(result['key2'], 'value2')
        # key3 is not in the result because the circular reference prevents reaching base_cache
        self.assertNotIn('key3', result)

    def test_debug_toolbar_scenario(self):
        """
        Simulate the Django Debug Toolbar scenario that triggered the original issue.
        Tests that the fix handles nested middleware caches correctly.
        """
        # Create a mock for the underlying Django Redis cache
        class MockRedisCache:
            def __init__(self):
                self.data = {}
            
            def get_many(self, keys):
                result = {}
                for k in keys:
                    result[k] = self.data.get(k, f'redis_value_{k}')
                return result
            
            def set(self, key, value, timeout=None):
                self.data[key] = value
        
        redis_cache = MockRedisCache()
        
        # Create a nested chain of AtomicCache instances
        django_cache = AtomicCache(redis_cache, 'default')
        debug_toolbar_cache = AtomicCache(django_cache, 'default')  # Debug Toolbar wraps
        silk_cache = AtomicCache(debug_toolbar_cache, 'default')    # Silk wraps
        
        # Add some values to different levels
        django_cache.set('django_key', 'django_value', None)
        debug_toolbar_cache.set('toolbar_key', 'toolbar_value', None)
        silk_cache.set('silk_key', 'silk_value', None)
        
        # Create a large set of keys to test
        test_keys = ['django_key', 'toolbar_key', 'silk_key'] + [f'key{i}' for i in range(1000)]
        
        # This should not cause recursion errors
        result = silk_cache.get_many(test_keys)
        
        # Verify that we got the expected values
        self.assertEqual(result['django_key'], 'django_value')
        self.assertEqual(result['toolbar_key'], 'toolbar_value')
        self.assertEqual(result['silk_key'], 'silk_value')
        
        # Verify that the remaining keys were fetched from the redis cache
        for i in range(10):
            key = f'key{i}'
            self.assertEqual(result[key], f'redis_value_{key}')
