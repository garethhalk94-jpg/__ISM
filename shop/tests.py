"""
Tests for the shop app: the cart, checkout and the invoice email.

Run with:  python manage.py test shop --noinput
"""

from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from shop.models import Order, Product, Store

User = get_user_model()
PASSWORD = "Str0ng-Test-Pass-123"

# Collect emails in memory instead of printing them. This is for Django 6.1,
# which reads MAILERS. Older versions are switched to in-memory email by
# Django's own test runner.
IN_MEMORY_EMAIL = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(
    MAILERS={"default": {"BACKEND": IN_MEMORY_EMAIL}},
)
class CheckoutTests(TestCase):
    """A buyer buys a product and receives an invoice."""

    @classmethod
    def setUpTestData(cls):
        """Create a vendor with a product and a buyer."""
        call_command("setup_groups", stdout=StringIO())
        vendor = User.objects.create_user("vendor", password=PASSWORD)
        vendor.groups.add(Group.objects.get(name="Vendors"))
        cls.buyer = User.objects.create_user(
            "buyer", email="buyer@example.com", password=PASSWORD
        )
        cls.buyer.groups.add(Group.objects.get(name="Buyers"))

        store = Store.objects.create(name="Test Store", vendor=vendor)
        cls.product = Product.objects.create(
            store=store,
            name="Widget",
            price=Decimal("10.00"),
            stock=5,
        )

    def add_to_cart(self, quantity):
        """Log in as the buyer and add the product to the cart."""
        self.client.force_login(self.buyer)
        return self.client.post(
            reverse("shop:add_item_to_cart", args=[self.product.pk]),
            {"quantity": quantity},
        )

    def test_checkout_creates_an_order_and_reduces_stock(self):
        """The order is saved, stock drops and the cart is emptied."""
        self.add_to_cart(2)
        response = self.client.post(reverse("shop:checkout"))

        order = Order.objects.get(buyer=self.buyer)
        self.assertRedirects(
            response,
            reverse("shop:invoice_confirmation", args=[order.pk]),
            fetch_redirect_response=False,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.total, Decimal("20.00"))
        self.assertEqual(self.client.session.get("cart"), {})

    def test_checkout_emails_the_invoice_to_the_buyer(self):
        """One invoice email is sent, listing the product and the total."""
        self.add_to_cart(2)
        self.client.post(reverse("shop:checkout"))

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["buyer@example.com"])
        self.assertIn("invoice", message.subject.lower())
        self.assertIn("Widget", message.body)
        self.assertIn("R20.00", message.body)

    def test_checkout_refuses_more_than_the_stock(self):
        """If stock falls below the cart quantity, no order is created."""
        self.add_to_cart(4)
        self.product.stock = 1
        self.product.save()

        self.client.post(reverse("shop:checkout"))

        self.assertFalse(Order.objects.exists())
        self.assertEqual(len(mail.outbox), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_empty_cart_cannot_be_checked_out(self):
        """Checking out with nothing in the cart creates nothing."""
        self.client.force_login(self.buyer)
        self.client.post(reverse("shop:checkout"))
        self.assertFalse(Order.objects.exists())
