from django.contrib.auth.models import Group, Permission
from django.db import transaction

"""
Roles and their permissions.
Roles are either Buyer or Vendor,
with Buyers only having 6 permissions
and Vendors having 8 permissions.
"""

ROLE_PERMISSIONS = {
    "Vendors": [
        "add_store",
        "change_store",
        "delete_store",
        "view_store",
        "add_product",
        "change_product",
        "delete_product",
        "view_product",
    ],
    "Buyers": [
        "view_store",
        "view_product",
        "add_review",
        "change_review",
        "delete_review",
        "view_review",
    ],
}


def apply_role_permissions(group):
    """
    Give a group the permissions defined for its role.

    Returns how many permissions the group now has.
    """

    permissions = Permission.objects.filter(
        content_type__app_label="shop",
        codename__in=ROLE_PERMISSIONS[group.name],
    )
    group.permissions.set(permissions)
    return permissions.count()


def get_role_group(name):
    """
    Return the group for a role, creating and equipping it if missing.
    """

    if name not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: {name}")

    with transaction.atomic():
        group, created = Group.objects.get_or_create(name=name)
        if created or not group.permissions.exists():
            apply_role_permissions(group)
    return group
