# coding: utf-8

from __future__ import unicode_literals
from collections import defaultdict
from datetime import datetime

from debug_toolbar.panels import Panel
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from django.utils.timesince import timesince

from .utils import _get_table_cache_key


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

    def disable_instrumentation(self):
        settings.CACHALOT_ENABLED = False

    def process_response(self, request, response):
        self.collect_invalidations()

    def collect_invalidations(self):
        models = apps.get_models()
        data = defaultdict(list)
        for db_alias in settings.DATABASES:
            model_cache_keys = dict(
                [(_get_table_cache_key(db_alias, model._meta.db_table), model)
                 for model in models])
            for cache_key, timestamp in cache.get_many(
                    model_cache_keys.keys()).items():
                invalidation = datetime.fromtimestamp(timestamp)
                model = model_cache_keys[cache_key]
                data[db_alias].append(
                    (model._meta.app_label, model.__name__, invalidation))
                if self.last_invalidation is None \
                        or invalidation > self.last_invalidation:
                    self.last_invalidation = invalidation
            data[db_alias].sort(key=lambda row: row[2], reverse=True)
        self.record_stats({'invalidations_per_db': data.items()})

    @property
    def nav_subtitle(self):
        if self.enabled and self.last_invalidation is not None:
            return (_('Last invalidation: %s')
                    % timesince(self.last_invalidation))
        return ''
