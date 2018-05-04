from django.conf import settings
from django.utils.module_loading import import_string


SUPPORTED_DATABASE_ENGINES = {
    'django.db.backends.sqlite3',
    'django.db.backends.postgresql',
    'django.db.backends.mysql',
    # TODO: Remove when we drop Django 2.x support.
    'django.db.backends.postgresql_psycopg2',

    # GeoDjango
    'django.contrib.gis.db.backends.spatialite',
    'django.contrib.gis.db.backends.postgis',
    'django.contrib.gis.db.backends.mysql',

    # django-transaction-hooks
    'transaction_hooks.backends.sqlite3',
    'transaction_hooks.backends.postgis',
    # TODO: Remove when we drop Django 2.x support.
    'transaction_hooks.backends.postgresql_psycopg2',
    'transaction_hooks.backends.mysql',
}

SUPPORTED_CACHE_BACKENDS = {
    'django.core.cache.backends.dummy.DummyCache',
    'django.core.cache.backends.locmem.LocMemCache',
    'django.core.cache.backends.filebased.FileBasedCache',
    'django_redis.cache.RedisCache',
    'django.core.cache.backends.memcached.MemcachedCache',
    'django.core.cache.backends.memcached.PyLibMCCache',
}

SUPPORTED_ONLY = 'supported_only'
ITERABLES = {tuple, list, frozenset, set}


class Settings(object):
    patched = False
    converters = {}

    CACHALOT_ENABLED = True
    CACHALOT_CACHE = 'default'
    CACHALOT_DATABASES = 'supported_only'
    CACHALOT_TIMEOUT = None
    CACHALOT_CACHE_RANDOM = False
    CACHALOT_INVALIDATE_RAW = True
    CACHALOT_ONLY_CACHABLE_TABLES = ()
    CACHALOT_UNCACHABLE_TABLES = ('django_migrations',)
    CACHALOT_QUERY_KEYGEN = 'cachalot.utils.get_query_cache_key'
    CACHALOT_TABLE_KEYGEN = 'cachalot.utils.get_table_cache_key'

    @classmethod
    def add_converter(cls, setting):
        def inner(func):
            cls.converters[setting] = func

        return inner

    @classmethod
    def get_names(cls):
        return {name for name in cls.__dict__
                if name[:2] != '__' and name.isupper()}

    def load(self):
        for name in self.get_names():
            value = getattr(settings, name, getattr(self.__class__, name))
            converter = self.converters.get(name)
            if converter is not None:
                value = converter(value)
            setattr(self, name, value)

        if not self.patched:
            from .monkey_patch import patch
            patch()
            self.patched = True

    def unload(self):
        if self.patched:
            from .monkey_patch import unpatch
            unpatch()
            self.patched = False

    def reload(self):
        self.unload()
        self.load()


@Settings.add_converter('CACHALOT_DATABASES')
def convert(value):
    if value == SUPPORTED_ONLY:
        value = {alias for alias, setting in settings.DATABASES.items()
                 if setting['ENGINE'] in SUPPORTED_DATABASE_ENGINES}
    if value.__class__ in ITERABLES:
        return frozenset(value)
    return value


@Settings.add_converter('CACHALOT_ONLY_CACHABLE_TABLES')
def convert(value):
    return frozenset(value)


@Settings.add_converter('CACHALOT_UNCACHABLE_TABLES')
def convert(value):
    return frozenset(value)


@Settings.add_converter('CACHALOT_QUERY_KEYGEN')
def convert(value):
    return import_string(value)


@Settings.add_converter('CACHALOT_TABLE_KEYGEN')
def convert(value):
    return import_string(value)


cachalot_settings = Settings()
