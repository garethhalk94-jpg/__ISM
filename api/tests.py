"""Automated tests for the REST API.

Run with:  python manage.py test api --noinput
"""

import base64
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from shop.models import Product, Review, Store

User = get_user_model()
PASSWORD = "Str0ng-Test-Pass-123"


def basic_auth(username, password=PASSWORD):
    """Return an HTTP Basic Authorization header value."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


class ApiTestBase(APITestCase):
    """Shared data: two vendors, a buyer, two stores, products, reviews."""

    @classmethod
    def make_user(cls, username, group_name):
        """Create a user in the named group."""
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=PASSWORD,
        )
        user.groups.add(Group.objects.get(name=group_name))
        return user

    @classmethod
    def setUpTestData(cls):
        """Create the groups, users, stores, products and reviews."""
        call_command("setup_groups", stdout=StringIO())

        cls.vendor1 = cls.make_user("vendor1", "Vendors")
        cls.vendor2 = cls.make_user("vendor2", "Vendors")
        cls.buyer = cls.make_user("buyer1", "Buyers")

        cls.store1 = Store.objects.create(name="Store One", vendor=cls.vendor1)
        cls.store2 = Store.objects.create(name="Store Two", vendor=cls.vendor2)
        cls.product1 = Product.objects.create(
            store=cls.store1,
            name="Widget",
            description="A widget",
            price=Decimal("9.99"),
            stock=5,
        )
        cls.product2 = Product.objects.create(
            store=cls.store2,
            name="Gizmo",
            description="A gizmo",
            price=Decimal("4.50"),
            stock=2,
        )
        cls.review1 = Review.objects.create(
            product=cls.product1,
            author=cls.buyer,
            rating=5,
            title="Great",
            body="Works well",
            is_verified=True,
        )
        cls.review2 = Review.objects.create(
            product=cls.product1,
            author=cls.buyer,
            rating=2,
            title="Meh",
            body="Not for me",
            is_verified=False,
        )
        cls.review3 = Review.objects.create(
            product=cls.product2,
            author=cls.buyer,
            rating=4,
            title="Good",
            body="Nice gizmo",
            is_verified=True,
        )

    def login_as(self, user):
        """Send this user's Basic Auth details with every request."""
        self.client.credentials(HTTP_AUTHORIZATION=basic_auth(user.username))

    def names(self, response, key="name"):
        """Return one field from every result on a paginated response."""
        return [item[key] for item in response.data["results"]]


class AuthenticationTests(ApiTestBase):
    """Every endpoint needs a valid login."""

    def test_request_without_login_is_rejected(self):
        """No credentials gives 401."""
        response = self.client.get(reverse("api:root"))
        self.assertEqual(response.status_code, 401)

    def test_wrong_password_is_rejected(self):
        """A wrong password gives 401."""
        self.client.credentials(
            HTTP_AUTHORIZATION=basic_auth("vendor1", "wrong-password")
        )
        response = self.client.get(reverse("api:root"))
        self.assertEqual(response.status_code, 401)


class EntryPointTests(ApiTestBase):
    """Each role is shown the entry points it should have."""

    def test_buyer_entry_points_are_vendors_stores_products(self):
        """A buyer is offered vendors, stores and products."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:root"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "buyer")
        self.assertEqual(
            sorted(response.data["entry_points"]),
            ["products", "stores", "vendors"],
        )

    def test_vendor_entry_points_are_stores_products_reviews(self):
        """A vendor is offered stores, products and reviews."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:root"))
        self.assertEqual(response.data["role"], "vendor")
        self.assertEqual(
            sorted(response.data["entry_points"]),
            ["products", "reviews", "stores"],
        )

    def test_entry_point_links_are_full_urls(self):
        """The links can be followed as they are."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:root"))
        link = response.data["entry_points"]["products"]
        self.assertTrue(link.startswith("http"))
        self.assertTrue(link.endswith("/api/v1/products/"))


class VendorListTests(ApiTestBase):
    """The vendors entry point."""

    def test_buyer_can_list_vendors(self):
        """Vendors are listed, buyers are not."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:vendors"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.names(response, "username"), ["vendor1", "vendor2"]
        )

    def test_vendor_list_shows_only_safe_fields(self):
        """No email address or password hash is exposed."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:vendors"))
        self.assertEqual(
            sorted(response.data["results"][0]), ["id", "username"]
        )


class StoreTests(ApiTestBase):
    """Creating and listing stores."""

    def test_vendor_can_create_store(self):
        """The new store belongs to the caller, whatever the body says."""
        self.login_as(self.vendor1)
        response = self.client.post(
            reverse("api:stores"),
            {"name": "New Shop", "vendor": self.vendor2.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        store = Store.objects.get(name="New Shop")
        self.assertEqual(store.vendor, self.vendor1)

    def test_buyer_cannot_create_store(self):
        """Buyers lack the add_store permission."""
        self.login_as(self.buyer)
        response = self.client.post(
            reverse("api:stores"), {"name": "Nope"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Store.objects.filter(name="Nope").exists())

    def test_store_name_is_required(self):
        """A blank name is a 400."""
        self.login_as(self.vendor1)
        response = self.client.post(
            reverse("api:stores"), {"name": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_buyer_sees_every_store(self):
        """The stores entry point shows all stores to a buyer."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:stores"))
        self.assertEqual(self.names(response), ["Store One", "Store Two"])

    def test_buyer_can_filter_stores_by_vendor(self):
        """?vendor=<id> narrows the list."""
        self.login_as(self.buyer)
        response = self.client.get(
            reverse("api:stores"), {"vendor": self.vendor2.pk}
        )
        self.assertEqual(self.names(response), ["Store Two"])

    def test_vendor_sees_only_own_stores(self):
        """The stores entry point is scoped to the vendor."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:stores"))
        self.assertEqual(self.names(response), ["Store One"])

    def test_filter_must_be_a_number(self):
        """A non-numeric filter is a 400, not a crash."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:stores"), {"vendor": "abc"})
        self.assertEqual(response.status_code, 400)

    def test_stores_listed_under_a_vendor(self):
        """The nested route lists one vendor's stores."""
        self.login_as(self.buyer)
        response = self.client.get(
            reverse("api:vendor_stores", args=[self.vendor1.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response), ["Store One"])

    def test_vendor_stores_for_a_non_vendor_gives_404(self):
        """A user who is not a vendor has no stores listing."""
        self.login_as(self.vendor1)
        response = self.client.get(
            reverse("api:vendor_stores", args=[self.buyer.pk])
        )
        self.assertEqual(response.status_code, 404)


class ProductTests(ApiTestBase):
    """Adding and listing products."""

    def test_vendor_can_add_product_to_own_store(self):
        """A vendor can add to a store they own."""
        self.login_as(self.vendor1)
        response = self.client.post(
            reverse("api:store_products", args=[self.store1.pk]),
            {
                "name": "Gadget",
                "description": "A gadget",
                "price": "19.99",
                "stock": 3,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        product = Product.objects.get(name="Gadget")
        self.assertEqual(product.store, self.store1)

    def test_vendor_cannot_add_product_to_another_vendors_store(self):
        """Ownership is enforced."""
        self.login_as(self.vendor2)
        response = self.client.post(
            reverse("api:store_products", args=[self.store1.pk]),
            {"name": "Sneaky", "price": "5.00", "stock": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.filter(name="Sneaky").exists())

    def test_buyer_cannot_add_product(self):
        """Buyers lack the add_product permission."""
        self.login_as(self.buyer)
        response = self.client.post(
            reverse("api:store_products", args=[self.store1.pk]),
            {"name": "Nope", "price": "5.00", "stock": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_product_values_are_rejected(self):
        """Bad prices and stock levels are 400s."""
        self.login_as(self.vendor1)
        url = reverse("api:store_products", args=[self.store1.pk])
        bad_values = [
            {"name": "Bad", "price": "-5", "stock": 1},
            {"name": "Bad", "price": "abc", "stock": 1},
            {"name": "Bad", "price": "1.234", "stock": 1},
            {"name": "Bad", "price": "5.00", "stock": -1},
        ]
        for data in bad_values:
            with self.subTest(data=data):
                response = self.client.post(url, data, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Product.objects.filter(name="Bad").exists())

    def test_buyer_sees_every_product(self):
        """The products entry point shows all products to a buyer."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:products"))
        self.assertEqual(self.names(response), ["Gizmo", "Widget"])

    def test_product_includes_its_store_name(self):
        """A product shows which store sells it."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:products"))
        gizmo = response.data["results"][0]
        self.assertEqual(gizmo["store_name"], "Store Two")

    def test_vendor_sees_only_own_products(self):
        """The products entry point is scoped to the vendor."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:products"))
        self.assertEqual(self.names(response), ["Widget"])

    def test_products_can_be_filtered_by_store(self):
        """?store=<id> narrows the list."""
        self.login_as(self.buyer)
        response = self.client.get(
            reverse("api:products"), {"store": self.store2.pk}
        )
        self.assertEqual(self.names(response), ["Gizmo"])

    def test_products_can_be_searched_by_name(self):
        """?search=<text> matches part of a name, ignoring case."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:products"), {"search": "WID"})
        self.assertEqual(self.names(response), ["Widget"])

    def test_a_stores_products(self):
        """The nested route lists only that store's products."""
        self.login_as(self.buyer)
        response = self.client.get(
            reverse("api:store_products", args=[self.store1.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response), ["Widget"])

    def test_products_of_unknown_store_give_404(self):
        """An unknown store id is a 404."""
        self.login_as(self.buyer)
        response = self.client.get(
            reverse("api:store_products", args=[999999])
        )
        self.assertEqual(response.status_code, 404)


class ReviewTests(ApiTestBase):
    """The vendor's review list and per-product reviews."""

    def test_vendor_review_list_covers_all_own_products(self):
        """One request returns reviews across all of the vendor's products."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:reviews"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(self.names(response, "title"), ["Meh", "Great"])

    def test_vendor_review_list_excludes_other_vendors_reviews(self):
        """A vendor never sees reviews of someone else's products."""
        self.login_as(self.vendor2)
        response = self.client.get(reverse("api:reviews"))
        self.assertEqual(self.names(response, "title"), ["Good"])

    def test_review_list_shows_author_and_product(self):
        """Each review names its author and product."""
        self.login_as(self.vendor2)
        response = self.client.get(reverse("api:reviews"))
        review = response.data["results"][0]
        self.assertEqual(review["author"], "buyer1")
        self.assertEqual(review["product_name"], "Gizmo")

    def test_buyer_cannot_use_the_review_list(self):
        """The review list is for vendors only."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:reviews"))
        self.assertEqual(response.status_code, 403)

    def test_reviews_can_be_filtered_by_rating(self):
        """?rating=<n> narrows the list."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:reviews"), {"rating": 2})
        self.assertEqual(self.names(response, "title"), ["Meh"])

    def test_reviews_can_be_filtered_by_verified(self):
        """?verified=true or false narrows the list."""
        self.login_as(self.vendor1)
        url = reverse("api:reviews")
        verified = self.client.get(url, {"verified": "true"})
        unverified = self.client.get(url, {"verified": "false"})
        self.assertEqual(self.names(verified, "title"), ["Great"])
        self.assertEqual(self.names(unverified, "title"), ["Meh"])

    def test_reviews_can_be_filtered_by_product(self):
        """?product=<id> narrows the list."""
        self.login_as(self.vendor1)
        response = self.client.get(
            reverse("api:reviews"), {"product": self.product1.pk}
        )
        self.assertEqual(response.data["count"], 2)

    def test_reviews_can_be_filtered_by_store(self):
        """?store=<id> narrows the list."""
        self.login_as(self.vendor1)
        response = self.client.get(
            reverse("api:reviews"), {"store": self.store2.pk}
        )
        # store2 belongs to vendor2, so vendor1 sees nothing in it.
        self.assertEqual(response.data["count"], 0)

    def test_bad_review_filters_are_400s(self):
        """Unusable filter values are rejected, not ignored."""
        self.login_as(self.vendor1)
        for params in ({"rating": "abc"}, {"verified": "maybe"}):
            with self.subTest(params=params):
                response = self.client.get(reverse("api:reviews"), params)
                self.assertEqual(response.status_code, 400)

    def test_vendor_can_read_reviews_of_one_product(self):
        """The per-product route works for the product's vendor."""
        self.login_as(self.vendor1)
        response = self.client.get(
            reverse("api:product_reviews", args=[self.product1.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_other_vendor_cannot_read_a_products_reviews(self):
        """Ownership is enforced on the per-product route."""
        self.login_as(self.vendor2)
        response = self.client.get(
            reverse("api:product_reviews", args=[self.product1.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_buyer_cannot_read_a_products_reviews_here(self):
        """Buyers are refused on the per-product route."""
        self.login_as(self.buyer)
        response = self.client.get(
            reverse("api:product_reviews", args=[self.product1.pk])
        )
        self.assertEqual(response.status_code, 403)


class PaginationTests(ApiTestBase):
    """Long lists are split into pages."""

    @classmethod
    def setUpTestData(cls):
        """Add 24 more products to store one, 26 in all."""
        super().setUpTestData()
        for number in range(24):
            Product.objects.create(
                store=cls.store1,
                name=f"Bulk {number:02d}",
                price=Decimal("1.00"),
                stock=1,
            )

    def test_first_page_has_twenty_results(self):
        """The default page size is 20, with a link to the next page."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:products"))
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])

    def test_second_page_has_the_rest(self):
        """?page=2 returns what is left."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:products"), {"page": 2})
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNone(response.data["next"])

    def test_page_size_can_be_changed(self):
        """?page_size=<n> changes how many come back."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:products"), {"page_size": 5})
        self.assertEqual(len(response.data["results"]), 5)

    def test_page_beyond_the_end_gives_404(self):
        """Asking for a page that does not exist is a 404."""
        self.login_as(self.vendor1)
        response = self.client.get(reverse("api:products"), {"page": 99})
        self.assertEqual(response.status_code, 404)


class RepresentationTests(ApiTestBase):
    """JSON is the default and XML can be requested."""

    def test_json_is_the_default_representation(self):
        """Without an Accept header the answer is JSON."""
        self.login_as(self.buyer)
        response = self.client.get(reverse("api:products"))
        self.assertIn("application/json", response["Content-Type"])

    def test_xml_can_be_requested(self):
        """Accept: application/xml returns XML."""
        self.login_as(self.buyer)
        response = self.client.get(
            reverse("api:products"), HTTP_ACCEPT="application/xml"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("xml", response["Content-Type"])
        self.assertIn(b"Widget", response.content)
