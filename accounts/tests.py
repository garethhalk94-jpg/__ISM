"""
Tests for registration and roles.

Run with:  python manage.py test accounts --noinput
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "Str0ng-Test-Pass-123"


class RegistrationTests(TestCase):
    """
    Registering as a vendor or a buyer, starting from an empty database.
    """

    def register(self, username, account_type, **overrides):
        """
        Post the registration form and return the response.
        """

        data = {
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "account_type": account_type,
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:register"), data)

    def test_database_starts_with_no_groups(self):
        """
        A fresh install has no groups, as on a reviewer's computer.
        """

        self.assertEqual(Group.objects.count(), 0)

    def test_vendor_can_register_on_a_fresh_database(self):
        """
        The Vendors group is created, with the right permissions.
        """

        response = self.register("newvendor", "vendors")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("shop:home"))

        user = User.objects.get(username="newvendor")
        self.assertEqual(
            list(user.groups.values_list("name", flat=True)), ["Vendors"]
        )
        self.assertTrue(user.has_perm("shop.add_store"))
        self.assertTrue(user.has_perm("shop.add_product"))
        self.assertFalse(user.has_perm("shop.add_review"))

    def test_buyer_can_register_on_a_fresh_database(self):
        """
        The Buyers group is created, with the right permissions.
        """

        response = self.register("newbuyer", "buyers")

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newbuyer")
        self.assertEqual(
            list(user.groups.values_list("name", flat=True)), ["Buyers"]
        )
        self.assertTrue(user.has_perm("shop.view_product"))
        self.assertTrue(user.has_perm("shop.add_review"))
        self.assertFalse(user.has_perm("shop.add_store"))

    def test_roles_are_created_once_not_per_registration(self):
        """
        A second vendor reuses the existing Vendors group.
        """

        self.register("vendor_a", "vendors")
        self.client.logout()
        self.register("vendor_b", "vendors")

        self.assertEqual(Group.objects.filter(name="Vendors").count(), 1)

    def test_an_existing_empty_group_is_given_its_permissions(self):
        """
        A group that exists but has no permissions is equipped.
        """

        Group.objects.create(name="Vendors")

        self.register("vendor_c", "vendors")

        user = User.objects.get(username="vendor_c")
        self.assertTrue(user.has_perm("shop.add_store"))

    def test_permissions_set_in_the_admin_are_not_overwritten(self):
        """
        A group an admin has already configured is left alone.
        """

        call_command("setup_groups", stdout=StringIO())
        vendors = Group.objects.get(name="Vendors")
        vendors.permissions.remove(
            vendors.permissions.get(codename="delete_store")
        )

        self.register("vendor_d", "vendors")

        user = User.objects.get(username="vendor_d")
        self.assertTrue(user.has_perm("shop.add_store"))
        self.assertFalse(user.has_perm("shop.delete_store"))

    def test_registered_vendor_can_open_the_create_store_page(self):
        """
        A new vendor can use a vendor-only page straight away.
        """

        self.register("vendor_e", "vendors")
        response = self.client.get(reverse("shop:create_store"))
        self.assertEqual(response.status_code, 200)

    def test_registered_buyer_is_refused_the_create_store_page(self):
        """
        A new buyer gets 403 on a vendor-only page.
        """

        self.register("buyer_e", "buyers")
        response = self.client.get(reverse("shop:create_store"))
        self.assertEqual(response.status_code, 403)

    def test_invalid_account_type_creates_no_user(self):
        """
        An unknown account type is refused.
        """

        response = self.register("nobody", "admins")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="nobody").exists())

    def test_weak_password_creates_no_user(self):
        """
        A weak password is refused.
        """

        response = self.register(
            "weak", "buyers", password="1234", password_confirm="1234"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak").exists())

    def test_duplicate_username_is_refused(self):
        """
        A second account cannot reuse a username.
        """

        self.register("dupe", "buyers")
        self.client.logout()
        response = self.register(
            "dupe", "buyers", email="different@example.com"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="dupe").count(), 1)


class SetupGroupsCommandTests(TestCase):
    """
    The setup_groups management command.
    """

    def test_command_creates_both_groups_with_permissions(self):
        """
        Vendors get 8 permissions and Buyers get 6.
        """

        out = StringIO()
        call_command("setup_groups", stdout=out)

        self.assertIn("Vendors: 8 permissions set", out.getvalue())
        self.assertIn("Buyers: 6 permissions set", out.getvalue())

    def test_command_can_be_run_twice(self):
        """
        Running it again does not duplicate the groups.
        """

        call_command("setup_groups", stdout=StringIO())
        call_command("setup_groups", stdout=StringIO())

        self.assertEqual(Group.objects.filter(name="Vendors").count(), 1)
        self.assertEqual(Group.objects.filter(name="Buyers").count(), 1)
