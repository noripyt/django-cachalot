from django import DJANGO_VERSION

VERSION = (2, 4, 2)
__version__ = ".".join(map(str, VERSION))

if DJANGO_VERSION < (3, 2):
    default_app_config = "cachalot.apps.CachalotConfig"
