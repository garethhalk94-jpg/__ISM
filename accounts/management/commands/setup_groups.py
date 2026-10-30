from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.roles import ROLE_PERMISSIONS, apply_role_permissions

"""
Management command that creates the Vendors and Buyers groups.
"""


class Command(BaseCommand):
    """
    Create or reset the Vendors and Buyers groups.
    """

    help = (
        "Create (or reset) the Vendors and Buyers groups with their "
        "permissions. Registration also does this automatically on demand."
    )

    def handle(self, *args, **options):
        """
        Create each group and give it the permissions for its role.
        """

        for name in ROLE_PERMISSIONS:
            group, _ = Group.objects.get_or_create(name=name)
            count = apply_role_permissions(group)
            self.stdout.write(f"{name}: {count} permissions set")
