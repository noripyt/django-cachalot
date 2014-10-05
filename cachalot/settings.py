from functools import wraps
from django.conf import settings


class SettingsOverrider(object):
    def __init__(self, settings, overrides):
        self.settings = settings
        self.overrides = overrides.items()
        self.originals = [(k, getattr(settings, k)) for k in overrides]

    def __enter__(self):
        for k, v in self.overrides:
            setattr(self.settings, k, v)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for k, v in self.originals:
            setattr(self.settings, k, v)

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner


class Settings(object):
    CACHALOT_ENABLED = True
    CACHALOT_CACHE = 'default'

    def __getattribute__(self, item):
        if hasattr(settings, item):
            return getattr(settings, item)
        return super(Settings, self).__getattribute__(item)

    def __call__(self, **kwargs):
        return SettingsOverrider(self, kwargs)


cachalot_settings = Settings()
