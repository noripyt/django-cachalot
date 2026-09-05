from django.core.signals import setting_changed
from django.dispatch import receiver

from ..settings import cachalot_settings
from .read import ReadTestCase, ParameterTypeTestCase
from .write import WriteTestCase, DatabaseCommandTestCase
from .transaction import AtomicCacheTestCase, AtomicTestCase
from .thread_safety import ThreadSafetyTestCase
from .multi_db import MultiDatabaseTestCase
from .settings import SettingsTestCase
from .api import APITestCase, CommandTestCase
from .signals import SignalsTestCase
from .issue_245 import Issue245RegressionTestCase
from .postgres import PostgresReadTestCase
from .debug_toolbar import DebugToolbarTestCase


@receiver(setting_changed)
def reload_settings(sender, **kwargs):
    cachalot_settings.reload()
