from django.conf import settings


class Settings(object):
    CACHALOT_ENABLED = True
    CACHALOT_CACHE = 'default'
    CACHALOT_TIMEOUT = None
    CACHALOT_CACHE_RANDOM = False
    CACHALOT_INVALIDATE_RAW = True
    CACHALOT_ONLY_CACHABLE_TABLES = frozenset()
    CACHALOT_UNCACHABLE_TABLES = frozenset(('django_migrations',))
    CACHALOT_QUERY_KEYGEN = 'cachalot.utils.get_query_cache_key'
    CACHALOT_TABLE_KEYGEN = 'cachalot.utils.get_table_cache_key'

    def __getattribute__(self, item):
        if hasattr(settings, item):
            return getattr(settings, item)
        return super(Settings, self).__getattribute__(item)

    def __setattr__(self, key, value):
        raise AttributeError(
            "Don't modify `cachalot_settings`, use "
            "`django.test.utils.override_settings` or "
            "`django.conf.settings` instead.")


cachalot_settings = Settings()
