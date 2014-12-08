from functools import wraps
from django.conf import settings


class SettingsOverrider(object):
    def __init__(self, settings, overrides):
        self.settings = settings
        self.overrides = overrides
        self.originals = [(k, getattr(settings, k)) for k in overrides]
        self.overridden = set(overrides) - settings.overridden

    def __enter__(self):
        self.settings.overridden.update(self.overridden)
        for k, v in self.overrides.items():
            setattr(self.settings, k, v)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for k, v in self.originals:
            setattr(self.settings, k, v)
        self.settings.overridden.difference_update(self.overridden)

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner


class Settings(object):
    CACHALOT_ENABLED = True
    CACHALOT_CACHE = 'default'
    CACHALOT_CACHE_RANDOM = False
    CACHALOT_INVALIDATE_RAW = True
    CACHALOT_QUERY_KEYGEN = 'cachalot.utils.get_query_cache_key'
    CACHALOT_TABLE_KEYGEN = 'cachalot.utils.get_table_cache_key'

    def __init__(self):
        self.overridden = set()

    def __getattribute__(self, item):
        overridden = super(Settings, self).__getattribute__('overridden')
        if hasattr(settings, item) and item not in overridden:
            return getattr(settings, item)
        return super(Settings, self).__getattribute__(item)

    def __call__(self, **kwargs):
        return SettingsOverrider(self, kwargs)


cachalot_settings = Settings()
