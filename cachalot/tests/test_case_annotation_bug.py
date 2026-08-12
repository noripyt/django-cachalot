from django.contrib.auth.models import Permission
from django.db.models import Case, When, BooleanField
from django.test import TransactionTestCase

from cachalot.tests.models import TestChild
from cachalot.api import invalidate


class TestAnnotationFilteringBug(TransactionTestCase):
    databases = ["default"]
    def get_child_permissions(self, child):
        # Dumb query which returns all Permission objects in a ManyToMany relationship
        perms = child.permissions.all().values_list("pk", flat=True)
        return Permission.objects.annotate(
            is_related=Case(When(pk__in=perms, then=True), default=False,
                            output_field=BooleanField())
        ).filter(is_related=True)

    def test_result_is_incorrectly_cached(self):
        child = TestChild.objects.create()
        permission_A, permission_B = Permission.objects.all()[:2]
        child.permissions.add(permission_A)
        self.assertEqual(len(self.get_child_permissions(child)), 1)
        self.assertSequenceEqual(self.get_child_permissions(child), [permission_A])
        child.permissions.add(permission_B)
        self.assertEqual(len(self.get_child_permissions(child)), 2)  # Fails
        self.assertSequenceEqual(
            self.get_child_permissions(child), [permission_A, permission_B]
        )

    def test_result_is_correct_if_cache_cleared(self):
        child = TestChild.objects.create()
        permission_A, permission_B = Permission.objects.all()[:2]
        child.permissions.add(permission_A)
        self.assertEqual(len(self.get_child_permissions(child)), 1)
        self.assertSequenceEqual(self.get_child_permissions(child), [permission_A])
        child.permissions.add(permission_B)
        invalidate(db_alias="default")
        self.assertEqual(len(self.get_child_permissions(child)), 2)  # Passes
        self.assertSequenceEqual(
            self.get_child_permissions(child), [permission_A, permission_B]
        )
