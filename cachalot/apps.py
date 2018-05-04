from __future__ import unicode_literals

from django import __version__ as django__version__, VERSION as django_version
from django.apps import AppConfig
from django.conf import settings
from django.core.checks import register, Tags, Warning, Error
from cachalot.utils import ITERABLES

from .settings import (
    cachalot_settings, SUPPORTED_CACHE_BACKENDS, SUPPORTED_DATABASE_ENGINES,
    SUPPORTED_ONLY)


@register(Tags.compatibility)
def check_django_version(app_configs, **kwargs):
    if not (1, 11) <= django_version < (2, 1):
        return [Error(
            'Django %s is not compatible with this version of django-cachalot.'
            % django__version__,
            hint='Refer to the django-cachalot documentation to find '
                 'which versions are compatible.',
            id='cachalot.E003')]
    return []


@register(Tags.caches, Tags.compatibility)
def check_cache_compatibility(app_configs, **kwargs):
    cache = settings.CACHES[cachalot_settings.CACHALOT_CACHE]
    cache_backend = cache['BACKEND']
    if cache_backend not in SUPPORTED_CACHE_BACKENDS:
        return [Warning(
            'Cache backend %r is not supported by django-cachalot.'
            % cache_backend,
            hint='Switch to a supported cache backend '
                 'like Redis or Memcached.',
            id='cachalot.W001')]
    return []


@register(Tags.database, Tags.compatibility)
def check_databases_compatibility(app_configs, **kwargs):
    errors = []
    databases = settings.DATABASES
    original_enabled_databases = getattr(settings, 'CACHALOT_DATABASES',
                                         SUPPORTED_ONLY)
    enabled_databases = cachalot_settings.CACHALOT_DATABASES
    if original_enabled_databases == SUPPORTED_ONLY:
        if not cachalot_settings.CACHALOT_DATABASES:
            errors.append(Warning(
                'None of the configured databases are supported '
                'by django-cachalot.',
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
                        'Database engine %r is not supported '
                        'by django-cachalot.' % engine,
                        hint='Switch to a supported database engine.',
                        id='cachalot.W003'
                    ))
            else:
                errors.append(Error(
                    'Database alias %r from `CACHALOT_DATABASES` '
                    'is not defined in `DATABASES`.' % db_alias,
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
            "`CACHALOT_DATABASES` must be either %r or a list, tuple, "
            "frozenset or set of database aliases." % SUPPORTED_ONLY,
            hint='Remove `CACHALOT_DATABASES` or change it.',
            id='cachalot.E002',
        ))
    return errors


class CachalotConfig(AppConfig):
    name = 'cachalot'

    def ready(self):
        cachalot_settings.load()
