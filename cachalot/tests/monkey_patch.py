# coding: utf-8

from unittest.mock import patch

from django.core.cache.backends.dummy import DummyCache as DjangoDummyCache
from django.test import TransactionTestCase

from .models import Test
from .test_utils import TestUtilsMixin


class DummyCache(DjangoDummyCache):
    def get_many(self, keys):
        ret = {}
        for k in keys:
            ret[k] = False

        return ret


class MonkeyPatchTestCase(TestUtilsMixin, TransactionTestCase):
    def setUp(self):
        super(MonkeyPatchTestCase, self).setUp()

        self.qs = Test.objects.create(name='test1')

    @patch('cachalot.cache.cachalot_caches.get_cache')
    def test_cache_get_many_invalid(self, get_cache):
        get_cache.return_value = DummyCache(host=None, params={})

        # Check DummyCache is response dummy response.
        from cachalot.cache import cachalot_caches
        ret = cachalot_caches.get_cache().get_many(['key1'])
        self.assertEqual(ret, {'key1': False})

        qs = Test.objects.get(name='test1')
        self.assertTrue(get_cache.called)
        self.assertEqual(qs.name, self.qs.name)

        Test.objects.create(name='test2')
        qs = Test.objects.all()
        for q in qs:
            self.assertIn(q.name, ['test1', 'test2'])
