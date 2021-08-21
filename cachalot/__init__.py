VERSION = (2, 4, 2)
__version__ = ".".join(map(str, VERSION))

try:
    from django import VERSION as DJANGO_VERSION

    if DJANGO_VERSION < (3, 2):
        default_app_config = "cachalot.apps.CachalotConfig"
except ImportError:
    default_app_config = "cachalot.apps.CachalotConfig"
