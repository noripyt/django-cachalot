from time import sleep
from unittest import skipIf

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import caches
from django.db import connection
from django.test.utils import override_settings

from ..api import invalidate
from ..settings import cachalot_settings
from .models import Test, TestParent
from .test_utils import TestUtilsMixin, FilteredTransactionTestCase


TABLE_OVERRIDES_AVAILABLE = len(settings.CACHES) > 1

OTHER_CACHE = next(
    (alias for alias in settings.CACHES if alias != 'default'), None
)


@skipIf(not TABLE_OVERRIDES_AVAILABLE,
        "Need at least two cache backends configured.")
class TableOverridesTestCase(TestUtilsMixin, FilteredTransactionTestCase):

    def setUp(self):
        super().setUp()
        for alias in settings.CACHES:
            caches[alias].clear()
        self.user = User.objects.create_user('user')
        self.t1 = Test.objects.create(name='test1', owner=self.user)

    def test_disabled_by_default(self):
        self.assertFalse(cachalot_settings.CACHALOT_TABLE_OVERRIDES)
        self.assert_query_cached(Test.objects.all(), [self.t1])

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'cache': OTHER_CACHE},
    })
    def test_per_table_cache(self):
        self.assert_query_cached(Test.objects.all(), [self.t1])

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'cache': OTHER_CACHE},
    })
    def test_write_invalidates_both_caches(self):
        self.assert_query_cached(Test.objects.all(), [self.t1])

        Test.objects.create(name='test2')

        with self.assertNumQueries(1):
            data = list(Test.objects.all())
        self.assertEqual(len(data), 2)

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'cache': OTHER_CACHE},
    })
    def test_mixed_table_query_uses_default(self):
        self.assert_query_cached(
            Test.objects.select_related('owner'), compare_results=False)

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'cache': OTHER_CACHE},
        'cachalot_testparent': {'cache': OTHER_CACHE},
    })
    def test_all_same_cache(self):
        TestParent.objects.create(name='parent1')
        self.assert_query_cached(Test.objects.all(), compare_results=False)
        self.assert_query_cached(
            TestParent.objects.all(), compare_results=False)

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'cache': OTHER_CACHE},
    })
    def test_api_invalidate(self):
        self.assert_query_cached(Test.objects.all(), [self.t1])

        invalidate(Test)

        with self.assertNumQueries(1):
            list(Test.objects.all())

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'cache': OTHER_CACHE},
    })
    def test_raw_sql_invalidation(self):
        self.assert_query_cached(Test.objects.all(), [self.t1])

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO cachalot_test (name, public) VALUES ('raw', 0);")

        with self.assertNumQueries(1):
            data = list(Test.objects.all())
        self.assertTrue(any(t.name == 'raw' for t in data))

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'cache': OTHER_CACHE},
    })
    def test_transaction_commit_invalidation(self):
        from django.db import transaction

        self.assert_query_cached(Test.objects.all(), [self.t1])

        with transaction.atomic():
            Test.objects.create(name='in_txn')

        with self.assertNumQueries(1):
            data = list(Test.objects.all())
        self.assertTrue(any(t.name == 'in_txn' for t in data))

    @override_settings(CACHALOT_TABLE_OVERRIDES={
        'cachalot_test': {'timeout': 1},
    })
    def test_per_table_timeout(self):
        self.assert_query_cached(Test.objects.all(), [self.t1])

        sleep(1)

        with self.assertNumQueries(1):
            list(Test.objects.all())
