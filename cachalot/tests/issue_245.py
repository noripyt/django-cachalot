"""
Regression tests for issue #245: when the cache backend is unreachable,
the ``post_migrate`` invalidate handler (path A) and ``AtomicCache.commit``
(path B, invoked from the patched ``Atomic.__exit__``) must not propagate
the cache exception out of Django's ``migrate`` command. Otherwise the
migration flow aborts before ``django_migrations`` is properly recorded,
and the next ``migrate`` run fails with ``relation "..." already exists``.

The cache backend here is patched to raise ``redis.exceptions.ConnectionError``
(or an equivalent ``OSError``) on writes; the patched handlers must still
return cleanly (and log a warning) instead of bubbling the exception up to
Django.
"""
import logging

from django.apps import apps
from django.core.cache import caches
from django.db import DEFAULT_DB_ALIAS
from django.test import TransactionTestCase

from ..monkey_patch import _invalidate_on_migration
from ..transaction import AtomicCache


class Issue245RegressionTestCase(TransactionTestCase):
    """Regression for https://github.com/noripyt/django-cachalot/issues/245"""

    def _patch_cache_to_raise(self, exc):
        cache = caches[DEFAULT_DB_ALIAS]
        original = cache.set_many

        def boom(*args, **kwargs):
            raise exc

        cache.set_many = boom
        return cache, original

    # -- Path A: post_migrate signal handler ---------------------------

    def test_post_migrate_handler_tolerates_redis_connection_error(self):
        from redis.exceptions import ConnectionError as RedisConnectionError

        sender = apps.get_app_config('auth')
        cache, original = self._patch_cache_to_raise(
            RedisConnectionError(
                'Error -2 connecting to redis:6379. '
                'Name or service not known.'),
        )
        try:
            with self.assertLogs('cachalot.monkey_patch',
                                 level='WARNING') as logs:
                # Must NOT raise. Must log a warning instead.
                _invalidate_on_migration(sender=sender,
                                         using=DEFAULT_DB_ALIAS)
        finally:
            cache.set_many = original

        # Sanity check: we did emit a warning mentioning the cache failure.
        self.assertTrue(
            any('django-cachalot' in m for m in logs.output),
            f'expected a warning from cachalot; got {logs.output!r}',
        )

    def test_post_migrate_handler_tolerates_generic_cache_exception(self):
        """Any cache backend failure should degrade, not abort migrate."""
        sender = apps.get_app_config('auth')
        cache, original = self._patch_cache_to_raise(
            OSError('simulated memcached/redis unreachable'),
        )
        try:
            with self.assertLogs('cachalot.monkey_patch',
                                 level='WARNING'):
                _invalidate_on_migration(sender=sender,
                                         using=DEFAULT_DB_ALIAS)
        finally:
            cache.set_many = original

    # -- Path B: AtomicCache.commit (called from Atomic.__exit__) --------

    def test_atomic_cache_commit_tolerates_cache_failure(self):
        """AtomicCache.commit() must not let a cache outage escape.

        ``commit()`` runs from inside Django's patched ``Atomic.__exit__``
        for every ``transaction.atomic()`` block, including each migration
        operation. If the parent cache raises here, the exception escapes
        the schema_editor's ``__exit__`` and aborts ``migrate`` before
        ``django_migrations`` rows are committed — see issue #245.
        """
        class _FailingParent(dict):
            def set_many(self, data, timeout):
                raise OSError('simulated cache outage')

        atomic_cache = AtomicCache(_FailingParent(), 'default')
        atomic_cache['k'] = (0.0, 'result')
        atomic_cache.to_be_invalidated.add('auth_user')

        with self.assertLogs('cachalot.transaction', level='WARNING') as logs:
            # Must NOT raise; must log a warning instead.
            atomic_cache.commit()

        self.assertTrue(
            any('django-cachalot' in m for m in logs.output),
            f'expected a warning from cachalot; got {logs.output!r}',
        )

    def test_atomic_cache_commit_tolerates_redis_connection_error(self):
        from redis.exceptions import ConnectionError as RedisConnectionError

        class _FailingParent(dict):
            def set_many(self, data, timeout):
                raise RedisConnectionError(
                    'Error -2 connecting to redis:6379.')

        atomic_cache = AtomicCache(_FailingParent(), 'default')
        atomic_cache['k'] = (0.0, 'result')
        atomic_cache.to_be_invalidated.add('auth_user')

        with self.assertLogs('cachalot.transaction', level='WARNING'):
            atomic_cache.commit()  # must NOT raise
