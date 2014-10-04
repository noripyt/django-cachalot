from django.conf import settings


CACHALOT_CACHE = getattr(settings, 'CACHALOT_CACHE', 'default')
