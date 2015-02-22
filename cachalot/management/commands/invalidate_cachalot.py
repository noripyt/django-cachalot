from optparse import make_option
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.db.models import get_app, get_model, get_models
from ...api import invalidate_all, invalidate_models


class Command(BaseCommand):
    help = 'Invalidates the cache keys set by django-cachalot.'
    args = '[app_label[.modelname] [...]]'
    option_list = BaseCommand.option_list + (
        make_option('-c', '--cache', action='store', dest='cache_alias',
                    type='choice', choices=list(settings.CACHES.keys()),
                    help='Cache alias from the CACHES setting.'),
        make_option('-d', '--db', action='store', dest='db_alias',
                    type='choice', choices=list(settings.DATABASES.keys()),
                    help='Database alias from the DATABASES setting.'),
    )

    def handle(self, *args, **options):
        cache_alias = options['cache_alias']
        db_alias = options['db_alias']
        verbosity = int(options['verbosity'])

        models = []
        for arg in args:
            try:
                app = get_app(arg)
            except ImproperlyConfigured:
                app_label = '.'.join(arg.split('.')[:-1])
                model_name = arg.split('.')[-1]
                models.append(get_model(app_label, model_name))
            else:
                models.extend(get_models(app))

        cache_str = '' if cache_alias is None else "on cache '%s'" % cache_alias
        db_str = '' if db_alias is None else "for database '%s'" % db_alias
        keys_str = 'keys for %s models' % len(models) if args else 'all keys'

        if verbosity > 0:
            self.stdout.write(' '.join(filter(bool, ['Invalidating', keys_str,
                                                     cache_str, db_str]))
                              + '...')

        if args:
            invalidate_models(models,
                              cache_alias=cache_alias, db_alias=db_alias)
        else:
            invalidate_all(cache_alias=cache_alias, db_alias=db_alias)
        if verbosity > 0:
            self.stdout.write('Cache keys successfully invalidated.')
