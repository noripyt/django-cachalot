from django.dispatch import Signal


post_invalidation = Signal(providing_args=['db_alias'])
