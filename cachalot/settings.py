from django.conf import settings


class Settings(object):
    CACHALOT_CACHE = 'default'

    def __getattribute__(self, item):
        if hasattr(settings, item):
            return getattr(settings, item)
        return super(Settings, self).__getattribute__(item)


cachalot_settings = Settings()
