from django import VERSION as django_version

from .read import ReadTestCase
from .write import WriteTestCase, DatabaseCommandTestCase
from .transaction import AtomicTestCase
from .thread_safety import ThreadSafetyTestCase
from .multi_db import MultiDatabaseTestCase
from .settings import SettingsTestCase
from .api import APITestCase, CommandTestCase
from .signals import SignalsTestCase
if django_version >= (1, 8):
    from .postgres import PostgresReadTest
