import copyreg
from django.apps import AppConfig
from django.conf import settings
from django.core.checks import register, Tags, Warning, Error
from cachalot.utils import ITERABLES

from .settings import (
    cachalot_settings, SUPPORTED_CACHE_BACKENDS, SUPPORTED_DATABASE_ENGINES,
    SUPPORTED_ONLY)


@register(Tags.caches, Tags.compatibility)
def check_cache_compatibility(app_configs, **kwargs):
    cache = settings.CACHES[cachalot_settings.CACHALOT_CACHE]
    cache_backend = cache['BACKEND']
    if cache_backend not in SUPPORTED_CACHE_BACKENDS:
        return [Warning(
            f'Cache backend {cache_backend} is not supported by django-cachalot.',
            hint='Switch to a supported cache backend like Redis or Memcached.',
            id='cachalot.W001')]
    return []


@register(Tags.database, Tags.compatibility)
def check_databases_compatibility(app_configs, **kwargs):
    errors = []
    databases = settings.DATABASES
    original_enabled_databases = getattr(settings, 'CACHALOT_DATABASES', SUPPORTED_ONLY)
    enabled_databases = cachalot_settings.CACHALOT_DATABASES
    if original_enabled_databases == SUPPORTED_ONLY:
        if not cachalot_settings.CACHALOT_DATABASES:
            errors.append(Warning(
                'None of the configured databases are supported by django-cachalot.',
                hint='Use a supported database, or remove django-cachalot, or '
                     'put at least one database alias in `CACHALOT_DATABASES` '
                     'to force django-cachalot to use it.',
                id='cachalot.W002'
            ))
    elif enabled_databases.__class__ in ITERABLES:
        for db_alias in enabled_databases:
            if db_alias in databases:
                engine = databases[db_alias]['ENGINE']
                if engine not in SUPPORTED_DATABASE_ENGINES:
                    errors.append(Warning(
                        f'Database engine {engine} is not supported '
                        'by django-cachalot.',
                        hint='Switch to a supported database engine.',
                        id='cachalot.W003',
                    ))
            else:
                errors.append(Error(
                    f'Database alias {db_alias} from `CACHALOT_DATABASES` '
                    'is not defined in `DATABASES`.',
                    hint='Change `CACHALOT_DATABASES` to be compliant with'
                         '`CACHALOT_DATABASES`',
                    id='cachalot.E001',
                ))

        if not enabled_databases:
            errors.append(Warning(
                'Django-cachalot is useless because no database '
                'is configured in `CACHALOT_DATABASES`.',
                hint='Reconfigure django-cachalot or remove it.',
                id='cachalot.W004'
            ))
    else:
        errors.append(Error(
            f"`CACHALOT_DATABASES` must be either {SUPPORTED_ONLY} or a list, tuple, "
            "frozenset or set of database aliases.",
            hint='Remove `CACHALOT_DATABASES` or change it.',
            id='cachalot.E002',
        ))
    return errors


class CachalotConfig(AppConfig):
    name = 'cachalot'

    def ready(self):
        # Cast memoryview objects to bytes to be able to pickle them.
        # https://docs.python.org/3/library/copyreg.html#copyreg.pickle
        copyreg.pickle(memoryview, lambda val: (memoryview, (bytes(val),)))
        cachalot_settings.load()
