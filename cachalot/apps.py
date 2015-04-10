from django.apps import AppConfig

from .monkey_patch import patch


class CachalotConfig(AppConfig):
    name = 'cachalot'
    patched = False

    def ready(self):
        if not self.patched:
            patch()
            self.patched = True
