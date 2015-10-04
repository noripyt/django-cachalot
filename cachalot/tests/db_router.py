from django.conf import settings


class PostgresRouter(object):
    @staticmethod
    def in_postgres(model):
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        return app_label == 'cachalot' and model_name == 'postgresmodel'

    def get_postgresql_alias(self):
        return ('postgresql' if 'postgresql' in settings.DATABASES
                else 'default')

    def allow_migrate(self, db, app_label, model=None, **hints):
        if hints.get('extension') in ('hstore', 'unaccent') \
                or (model is not None and self.in_postgres(model)):
            return db == self.get_postgresql_alias()
