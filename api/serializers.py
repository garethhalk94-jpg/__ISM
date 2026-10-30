"""Serializers: how models become JSON or XML, and back again."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from shop.models import Product, Review, Store

User = get_user_model()


class VendorSerializer(serializers.ModelSerializer):
    """A vendor as buyers see them: an id and a username, nothing private."""

    class Meta:
        """Serializer options."""

        model = User
        fields = ["id", "username"]
        read_only_fields = fields


class StoreSerializer(serializers.ModelSerializer):
    """A store, with its vendor's id and name."""

    vendor_name = serializers.CharField(
        source="vendor.username", read_only=True
    )

    class Meta:
        """Serializer options."""

        model = Store
        fields = ["id", "name", "vendor", "vendor_name"]
        # The vendor is set from the login, never accepted from the client.
        read_only_fields = ["vendor"]


class ProductSerializer(serializers.ModelSerializer):
    """A product, with the id and name of the store that sells it."""

    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        """Serializer options."""

        model = Product
        fields = [
            "id",
            "store",
            "store_name",
            "name",
            "description",
            "price",
            "stock",
        ]
        # The store comes from the URL, not from the request body.
        read_only_fields = ["store"]


class ReviewSerializer(serializers.ModelSerializer):
    """A review, read-only, with its author's username and product name."""

    author = serializers.CharField(source="author.username", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        """Serializer options."""

        model = Review
        fields = [
            "id",
            "product",
            "product_name",
            "author",
            "rating",
            "title",
            "body",
            "created_at",
            "is_verified",
        ]
        read_only_fields = fields
