from django.apps import AppConfig
from django.conf import settings
from django.core.checks import register, Tags, Error

from .monkey_patch import patch
from .settings import cachalot_settings


VALID_DATABASE_ENGINES = {
    'django.db.backends.sqlite3',
    'django.db.backends.postgresql',
    'django.db.backends.mysql',
    # TODO: Remove when we drop Django 1.8 support.
    'django.db.backends.postgresql_psycopg2',

    # GeoDjango
    'django.contrib.gis.db.backends.spatialite',
    'django.contrib.gis.db.backends.postgis',
    'django.contrib.gis.db.backends.mysql',

    # django-transaction-hooks
    'transaction_hooks.backends.sqlite3',
    'transaction_hooks.backends.postgis',
    'transaction_hooks.backends.postgresql_psycopg2',
    'transaction_hooks.backends.mysql',
}


VALID_CACHE_BACKENDS = {
    'django.core.cache.backends.dummy.DummyCache',
    'django.core.cache.backends.locmem.LocMemCache',
    'django.core.cache.backends.filebased.FileBasedCache',
    'django_redis.cache.RedisCache',
    'django.core.cache.backends.memcached.MemcachedCache',
    'django.core.cache.backends.memcached.PyLibMCCache',
}


@register(Tags.compatibility)
def check_compatibility(app_configs, **kwargs):
    cache_alias = cachalot_settings.CACHALOT_CACHE
    caches = {cache_alias: settings.CACHES[cache_alias]}

    errors = []
    for setting, k, valid_values in (
            (settings.DATABASES, 'ENGINE', VALID_DATABASE_ENGINES),
            (caches, 'BACKEND', VALID_CACHE_BACKENDS)):
        for config in setting.values():
            value = config[k]
            if value not in valid_values:
                errors.append(
                    Error(
                        '`%s` is not compatible with django-cachalot.' % value,
                        id='cachalot.E001',
                    )
                )
    return errors


class CachalotConfig(AppConfig):
    name = 'cachalot'
    patched = False

    def ready(self):
        if not self.patched:
            patch()
            self.patched = True
