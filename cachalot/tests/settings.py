from time import sleep
from unittest import skipIf

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.core.checks import run_checks, Tags, Warning, Error
from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import override_settings

from ..api import invalidate
from ..settings import SUPPORTED_ONLY, SUPPORTED_DATABASE_ENGINES
from .models import Test, TestParent, TestChild, UnmanagedModel
from .test_utils import TestUtilsMixin


class SettingsTestCase(TestUtilsMixin, TransactionTestCase):
    @override_settings(CACHALOT_ENABLED=False)
    def test_decorator(self):
        self.assert_query_cached(Test.objects.all(), after=1)

    def test_django_override(self):
        with self.settings(CACHALOT_ENABLED=False):
            qs = Test.objects.all()
            self.assert_query_cached(qs, after=1)
            with self.settings(CACHALOT_ENABLED=True):
                self.assert_query_cached(qs)

    def test_enabled(self):
        qs = Test.objects.all()

        with self.settings(CACHALOT_ENABLED=True):
            self.assert_query_cached(qs)

        with self.settings(CACHALOT_ENABLED=False):
            self.assert_query_cached(qs, after=1)

        with self.assertNumQueries(0):
            list(Test.objects.all())

        with self.settings(CACHALOT_ENABLED=False):
            with self.assertNumQueries(1):
                t = Test.objects.create(name='test')
        with self.assertNumQueries(1):
            data = list(Test.objects.all())
        self.assertListEqual(data, [t])

    @skipIf(len(settings.CACHES) == 1, 'We can’t change the cache used '
                                       'since there’s only one configured.')
    def test_cache(self):
        other_cache_alias = next(alias for alias in settings.CACHES
                                 if alias != DEFAULT_CACHE_ALIAS)
        invalidate(Test, cache_alias=other_cache_alias)

        qs = Test.objects.all()

        with self.settings(CACHALOT_CACHE=DEFAULT_CACHE_ALIAS):
            self.assert_query_cached(qs)

        with self.settings(CACHALOT_CACHE=other_cache_alias):
            self.assert_query_cached(qs)

        Test.objects.create(name='test')

        # Only `CACHALOT_CACHE` is invalidated, so changing the database should
        # not invalidate all caches.
        with self.settings(CACHALOT_CACHE=other_cache_alias):
            self.assert_query_cached(qs, before=0)

    def test_databases(self):
        qs = Test.objects.all()
        with self.settings(CACHALOT_DATABASES=SUPPORTED_ONLY):
            self.assert_query_cached(qs)

        invalidate(Test)

        engine = connection.settings_dict['ENGINE']
        SUPPORTED_DATABASE_ENGINES.remove(engine)
        with self.settings(CACHALOT_DATABASES=SUPPORTED_ONLY):
            self.assert_query_cached(qs, after=1)
        SUPPORTED_DATABASE_ENGINES.add(engine)
        with self.settings(CACHALOT_DATABASES=SUPPORTED_ONLY):
            self.assert_query_cached(qs)

        with self.settings(CACHALOT_DATABASES=[]):
            self.assert_query_cached(qs, after=1)

    def test_cache_timeout(self):
        qs = Test.objects.all()

        with self.assertNumQueries(1):
            list(qs.all())
        sleep(1)
        with self.assertNumQueries(0):
            list(qs.all())

        invalidate(Test)

        with self.settings(CACHALOT_TIMEOUT=0):
            with self.assertNumQueries(1):
                list(qs.all())
            sleep(0.05)
            with self.assertNumQueries(1):
                list(qs.all())

        # We have to test with a full second and not a shorter time because
        # memcached only takes the integer part of the timeout into account.
        with self.settings(CACHALOT_TIMEOUT=1):
            self.assert_query_cached(qs)
            sleep(1)
            with self.assertNumQueries(1):
                list(Test.objects.all())

    def test_cache_random(self):
        qs = Test.objects.order_by('?')
        self.assert_query_cached(qs, after=1, compare_results=False)

        with self.settings(CACHALOT_CACHE_RANDOM=True):
            self.assert_query_cached(qs)

    def test_invalidate_raw(self):
        with self.assertNumQueries(1):
            list(Test.objects.all())
        with self.settings(CACHALOT_INVALIDATE_RAW=False):
            with self.assertNumQueries(1):
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE %s SET name = 'new name';"
                                   % Test._meta.db_table)
        with self.assertNumQueries(0):
            list(Test.objects.all())

    def test_only_cachable_tables(self):
        with self.settings(CACHALOT_ONLY_CACHABLE_TABLES=('cachalot_test',)):
            self.assert_query_cached(Test.objects.all())
            self.assert_query_cached(TestParent.objects.all(), after=1)
            self.assert_query_cached(Test.objects.select_related('owner'),
                                     after=1)

        self.assert_query_cached(TestParent.objects.all())

        with self.settings(CACHALOT_ONLY_CACHABLE_TABLES=(
                'cachalot_test', 'cachalot_testchild', 'auth_user')):
            self.assert_query_cached(Test.objects.select_related('owner'))

            # TestChild uses multi-table inheritance, and since its parent,
            # 'cachalot_testparent', is not cachable, a basic
            # TestChild query can’t be cached
            self.assert_query_cached(TestChild.objects.all(), after=1)

            # However, if we only fetch data from the 'cachalot_testchild'
            # table, it’s cachable.
            self.assert_query_cached(TestChild.objects.values('public'))

    @override_settings(CACHALOT_ONLY_CACHABLE_APPS=('cachalot',))
    def test_only_cachable_apps(self):
        self.assert_query_cached(Test.objects.all())
        self.assert_query_cached(TestParent.objects.all())
        self.assert_query_cached(Test.objects.select_related('owner'), after=1)

    # Must use override_settings to get the correct effect. Using the cm doesn't
    # reload settings on cachalot's side
    @override_settings(CACHALOT_ONLY_CACHABLE_TABLES=('cachalot_test', 'auth_user'),
                       CACHALOT_ONLY_CACHABLE_APPS=('cachalot',))
    def test_only_cachable_apps_set_combo(self):
        self.assert_query_cached(Test.objects.all())
        self.assert_query_cached(TestParent.objects.all())
        self.assert_query_cached(Test.objects.select_related('owner'))

    def test_uncachable_tables(self):
        qs = Test.objects.all()

        with self.settings(CACHALOT_UNCACHABLE_TABLES=('cachalot_test',)):
            self.assert_query_cached(qs, after=1)

        self.assert_query_cached(qs)

        with self.settings(CACHALOT_UNCACHABLE_TABLES=('cachalot_test',)):
            self.assert_query_cached(qs, after=1)

    @override_settings(CACHALOT_UNCACHABLE_APPS=('cachalot',))
    def test_uncachable_apps(self):
        self.assert_query_cached(Test.objects.all(), after=1)
        self.assert_query_cached(TestParent.objects.all(), after=1)

    @override_settings(CACHALOT_UNCACHABLE_TABLES=('cachalot_test',),
                       CACHALOT_UNCACHABLE_APPS=('cachalot',))
    def test_uncachable_apps_set_combo(self):
        self.assert_query_cached(Test.objects.all(), after=1)
        self.assert_query_cached(TestParent.objects.all(), after=1)

    def test_only_cachable_and_uncachable_table(self):
        with self.settings(
                CACHALOT_ONLY_CACHABLE_TABLES=('cachalot_test',
                                               'cachalot_testparent'),
                CACHALOT_UNCACHABLE_TABLES=('cachalot_test',)):
            self.assert_query_cached(Test.objects.all(), after=1)
            self.assert_query_cached(TestParent.objects.all())
            self.assert_query_cached(User.objects.all(), after=1)

    def test_uncachable_unmanaged_table(self):
        qs = UnmanagedModel.objects.all()
        with self.settings(
            CACHALOT_UNCACHABLE_TABLES=("cachalot_unmanagedmodel",),
            CACHALOT_ADDITIONAL_TABLES=("cachalot_unmanagedmodel",)
        ):
            self.assert_query_cached(qs, after=1)

    def test_cache_compatibility(self):
        compatible_cache = {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
        incompatible_cache = {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table'
        }

        with self.settings(CACHES={'default': compatible_cache,
                                   'secondary': incompatible_cache}):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [])

        warning001 = Warning(
            'Cache backend %r is not supported by django-cachalot.'
            % 'django.core.cache.backends.db.DatabaseCache',
            hint='Switch to a supported cache backend '
                 'like Redis or Memcached.',
            id='cachalot.W001')
        with self.settings(CACHES={'default': incompatible_cache}):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [warning001])
        with self.settings(CACHES={'default': compatible_cache,
                                   'secondary': incompatible_cache},
                           CACHALOT_CACHE='secondary'):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [warning001])

    def test_database_compatibility(self):
        compatible_database = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'non_existent_db.sqlite3',
        }
        incompatible_database = {
            'ENGINE': 'django.db.backends.oracle',
            'NAME': 'non_existent_db',
        }

        warning002 = Warning(
            'None of the configured databases are supported '
            'by django-cachalot.',
            hint='Use a supported database, or remove django-cachalot, or '
                 'put at least one database alias in `CACHALOT_DATABASES` '
                 'to force django-cachalot to use it.',
            id='cachalot.W002'
        )
        warning003 = Warning(
            'Database engine %r is not supported by django-cachalot.'
            % 'django.db.backends.oracle',
            hint='Switch to a supported database engine.',
            id='cachalot.W003'
        )
        warning004 = Warning(
            'Django-cachalot is useless because no database '
            'is configured in `CACHALOT_DATABASES`.',
            hint='Reconfigure django-cachalot or remove it.',
            id='cachalot.W004'
        )
        error001 = Error(
            'Database alias %r from `CACHALOT_DATABASES` '
            'is not defined in `DATABASES`.' % 'secondary',
            hint='Change `CACHALOT_DATABASES` to be compliant with'
                 '`CACHALOT_DATABASES`',
            id='cachalot.E001',
        )
        error002 = Error(
            "`CACHALOT_DATABASES` must be either %r or a list, tuple, "
            "frozenset or set of database aliases." % SUPPORTED_ONLY,
            hint='Remove `CACHALOT_DATABASES` or change it.',
            id='cachalot.E002',
        )

        with self.settings(DATABASES={'default': incompatible_database}):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [warning002])

        with self.settings(DATABASES={'default': compatible_database,
                                      'secondary': incompatible_database}):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [])
        with self.settings(DATABASES={'default': incompatible_database,
                                      'secondary': compatible_database}):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [])

        with self.settings(DATABASES={'default': incompatible_database},
                           CACHALOT_DATABASES=['default']):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [warning003])

        with self.settings(DATABASES={'default': incompatible_database},
                           CACHALOT_DATABASES=[]):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [warning004])

        with self.settings(DATABASES={'default': incompatible_database},
                           CACHALOT_DATABASES=['secondary']):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [error001])
        with self.settings(DATABASES={'default': compatible_database},
                           CACHALOT_DATABASES=['default', 'secondary']):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [error001])

        with self.settings(CACHALOT_DATABASES='invalid value'):
            errors = run_checks(tags=[Tags.compatibility])
            self.assertListEqual(errors, [error002])
