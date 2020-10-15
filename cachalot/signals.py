from django.dispatch import Signal

# The argument "providing_args=['db_alias']" is deprecated and purely documentational.
# TODO: Write a explaining text to what "db_alias" is supposed to document.
post_invalidation = Signal()
