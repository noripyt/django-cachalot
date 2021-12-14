from collections import defaultdict
from datetime import datetime

from debug_toolbar.panels import Panel
from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.timesince import timesince

from cachalot.tenants import tenant_handler
from .cache import cachalot_caches
from .settings import cachalot_settings


class CachalotPanel(Panel):
    title = 'Cachalot'
    template = 'cachalot/panel.html'

    def __init__(self, *args, **kwargs):
        self.last_invalidation = None
        super(CachalotPanel, self).__init__(*args, **kwargs)

    @property
    def enabled(self):
        enabled = super(CachalotPanel, self).enabled
        if enabled:
            self.enable_instrumentation()
        else:
            self.disable_instrumentation()
        return enabled

    def enable_instrumentation(self):
        settings.CACHALOT_ENABLED = True
        cachalot_settings.reload()

    def disable_instrumentation(self):
        settings.CACHALOT_ENABLED = False
        cachalot_settings.reload()

    def process_request(self, request):
        self.collect_invalidations()
        return super(CachalotPanel, self).process_request(request)

    def collect_invalidations(self):
        models = apps.get_models()
        data = defaultdict(list)
        multi_tenant_dbs = []
        cache = cachalot_caches.get_cache()
        for db_alias in settings.DATABASES:
            get_table_cache_key = cachalot_settings.CACHALOT_TABLE_KEYGEN
            model_cache_keys = {
                get_table_cache_key(db_alias, model._meta.db_table): model
                for model in models}
            for cache_key, timestamp in cache.get_many(
                    model_cache_keys.keys()).items():
                invalidation = datetime.fromtimestamp(timestamp)
                model = model_cache_keys[cache_key]
                model_name = model.__name__
                if (
                    tenant_handler.is_multi_tenant_database(db_alias) and
                    cache_key not in tenant_handler.public_schema_keys
                ):
                    # Add indicator to show that this cached model is tenant-specific.
                    model_name = '{}*'.format(model_name)
                data[db_alias].append(
                    (model._meta.app_label, model_name, invalidation))
                if self.last_invalidation is None \
                        or invalidation > self.last_invalidation:
                    self.last_invalidation = invalidation
            data[db_alias].sort(key=lambda row: row[2], reverse=True)
            if tenant_handler.is_multi_tenant_database(db_alias):
                multi_tenant_dbs.append(db_alias)
        self.record_stats(
            {
                'invalidations_per_db': data.items(),
                'multi_tenant_dbs': multi_tenant_dbs

            }
        )

    @property
    def nav_subtitle(self):
        if self.enabled and self.last_invalidation is not None:
            return (_('Last invalidation: %s')
                    % timesince(self.last_invalidation))
        return ''
