import logging
from functools import wraps

from django.core.cache import cache
from django.test.utils import override_settings

logger = logging.getLogger(__name__)


def all_final_sql_checks(func):
    """
    Runs test as two sub-tests:
    one with CACHALOT_FINAL_SQL_CHECK setting True, one with False
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        for final_sql_check in (True, False):
            with self.subTest(msg=f'CACHALOT_FINAL_SQL_CHECK = {final_sql_check}'):
                with override_settings(
                        CACHALOT_FINAL_SQL_CHECK=final_sql_check
                ):
                    func(self, *args, **kwargs)
            cache.clear()

    return wrapper


def no_final_sql_check(func):
    """
    Runs test with CACHALOT_FINAL_SQL_CHECK = False
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with override_settings(CACHALOT_FINAL_SQL_CHECK=False):
            func(self, *args, **kwargs)

    return wrapper


def with_final_sql_check(func):
    """
    Runs test with CACHALOT_FINAL_SQL_CHECK = True
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with override_settings(CACHALOT_FINAL_SQL_CHECK=True):
            func(self, *args, **kwargs)

    return wrapper
