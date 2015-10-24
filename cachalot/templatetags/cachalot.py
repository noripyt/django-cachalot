from django.apps import apps
from django.template import Library

from ..api import get_last_invalidation as get_last_invalidation_function


register = Library()


@register.assignment_tag
def get_last_invalidation(*tables_or_model_lookups, **kwargs):
    tables_or_models = []
    for table_or_model_lookup in tables_or_model_lookups:
        if '.' in table_or_model_lookup:
            tables_or_models.append(apps.get_model(table_or_model_lookup))
        else:
            tables_or_models.append(table_or_model_lookup)
    return get_last_invalidation_function(*tables_or_models, **kwargs)
