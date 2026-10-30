"""REST API views (version 1).

Every endpoint applies the same three layers as the website:

1. Authentication (HTTP Basic): who is calling?
2. Permission: does the user's group allow this action?
3. Ownership: is this the user's own store or product?

Entry points
    Buyers:  vendors, stores and products (everything is visible).
    Vendors: stores and products (their own) and reviews of their products.
"""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shop.models import Product, Review, Store

from .serializers import (
    ProductSerializer,
    ReviewSerializer,
    StoreSerializer,
    VendorSerializer,
)

User = get_user_model()


class StandardPagination(PageNumberPagination):
    """Page results 20 at a time. Clients may ask for up to 100."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def is_vendor(user):
    """Return True if the user belongs to the Vendors group."""
    return user.groups.filter(name="Vendors").exists()


def forbidden(message):
    """Return a 403 response with an error message."""
    return Response({"error": message}, status=status.HTTP_403_FORBIDDEN)


def bad_request(message):
    """Return a 400 response with an error message."""
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def paginated(request, queryset, serializer_class):
    """Return one page of a queryset, serialised, with paging links."""
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(page, many=True)
    return paginator.get_paginated_response(serializer.data)


def int_filters(request, *names):
    """Return {name: int} for each named query parameter that is present.

    Raises ValueError, naming the parameter, if a value is not a whole
    number.
    """
    filters = {}
    for name in names:
        raw = request.query_params.get(name)
        if raw in (None, ""):
            continue
        try:
            filters[name] = int(raw)
        except ValueError:
            raise ValueError(f"'{name}' must be a whole number.") from None
    return filters


@api_view(["GET"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def api_root(request):
    """GET /api/v1/ - list the entry points available to the caller."""

    def link(name):
        """Return the full URL of a named endpoint."""
        return request.build_absolute_uri(reverse(f"api:{name}"))

    if is_vendor(request.user):
        role = "vendor"
        names = ["stores", "products", "reviews"]
    else:
        role = "buyer"
        names = ["vendors", "stores", "products"]
    return Response(
        {"role": role, "entry_points": {name: link(name) for name in names}}
    )


@api_view(["GET"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def vendor_list(request):
    """GET /api/v1/vendors/ - every vendor, for buyers and vendors."""
    if not request.user.has_perm("shop.view_store"):
        return forbidden("You do not have permission to view vendors.")

    vendors = User.objects.filter(groups__name="Vendors").order_by("username")
    return paginated(request, vendors, VendorSerializer)


@api_view(["GET", "POST"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def stores(request):
    """GET: list stores. POST: a vendor creates a store.

    Vendors see their own stores. Buyers see every store and may narrow
    the list with ?vendor=<id>.
    """
    if request.method == "POST":
        if not request.user.has_perm("shop.add_store"):
            return forbidden("You do not have permission to create stores.")

        serializer = StoreSerializer(data=request.data)
        if serializer.is_valid():
            # The vendor always comes from the login, never the request.
            serializer.save(vendor=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if not request.user.has_perm("shop.view_store"):
        return forbidden("You do not have permission to view stores.")

    queryset = Store.objects.select_related("vendor").order_by("name", "id")
    if is_vendor(request.user):
        queryset = queryset.filter(vendor=request.user)
    else:
        try:
            filters = int_filters(request, "vendor")
        except ValueError as exc:
            return bad_request(str(exc))
        if "vendor" in filters:
            queryset = queryset.filter(vendor_id=filters["vendor"])
    return paginated(request, queryset, StoreSerializer)


@api_view(["GET"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def products(request):
    """GET /api/v1/products/ - vendors see their own, buyers see all.

    Narrow the list with ?store=<id> and ?search=<text> (name contains).
    """
    if not request.user.has_perm("shop.view_product"):
        return forbidden("You do not have permission to view products.")

    queryset = Product.objects.select_related("store").order_by("name", "id")
    if is_vendor(request.user):
        queryset = queryset.filter(store__vendor=request.user)

    try:
        filters = int_filters(request, "store")
    except ValueError as exc:
        return bad_request(str(exc))
    if "store" in filters:
        queryset = queryset.filter(store_id=filters["store"])

    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return paginated(request, queryset, ProductSerializer)


@api_view(["GET"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def reviews(request):
    """GET /api/v1/reviews/ - every review of the vendor's own products.

    Newest first. Narrow the list with ?store=<id>, ?product=<id>,
    ?rating=<number> and ?verified=true or ?verified=false.
    """
    if not is_vendor(request.user):
        return forbidden("Only vendors can list reviews.")

    queryset = (
        Review.objects.filter(product__store__vendor=request.user)
        .select_related("product", "author")
        .order_by("-created_at", "-id")
    )

    try:
        filters = int_filters(request, "store", "product", "rating")
    except ValueError as exc:
        return bad_request(str(exc))
    if "store" in filters:
        queryset = queryset.filter(product__store_id=filters["store"])
    if "product" in filters:
        queryset = queryset.filter(product_id=filters["product"])
    if "rating" in filters:
        queryset = queryset.filter(rating=filters["rating"])

    verified = request.query_params.get("verified", "").strip().lower()
    if verified in ("true", "1"):
        queryset = queryset.filter(is_verified=True)
    elif verified in ("false", "0"):
        queryset = queryset.filter(is_verified=False)
    elif verified:
        return bad_request("'verified' must be true or false.")
    return paginated(request, queryset, ReviewSerializer)


@api_view(["GET"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def vendor_stores(request, vendor_id):
    """GET /api/v1/vendors/<id>/stores/ - the stores listed under a vendor."""
    if not request.user.has_perm("shop.view_store"):
        return forbidden("You do not have permission to view stores.")

    vendor = get_object_or_404(User, pk=vendor_id, groups__name="Vendors")
    queryset = vendor.stores.select_related("vendor").order_by("name", "id")
    return paginated(request, queryset, StoreSerializer)


@api_view(["GET", "POST"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def store_products(request, store_id):
    """GET: the products of a store. POST: its vendor adds a product."""
    store = get_object_or_404(Store, pk=store_id)

    if request.method == "GET":
        if not request.user.has_perm("shop.view_product"):
            return forbidden("You do not have permission to view products.")
        queryset = store.products.select_related("store").order_by(
            "name", "id"
        )
        return paginated(request, queryset, ProductSerializer)

    # POST: permission first, then ownership of this particular store.
    if not request.user.has_perm("shop.add_product"):
        return forbidden("You do not have permission to add products.")
    if store.vendor_id != request.user.pk:
        return forbidden("You can only add products to your own stores.")

    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(store=store)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([BasicAuthentication])
@permission_classes([IsAuthenticated])
def product_reviews(request, product_id):
    """GET /api/v1/products/<id>/reviews/ - for the product's own vendor."""
    product = get_object_or_404(
        Product.objects.select_related("store"), pk=product_id
    )
    if product.store.vendor_id != request.user.pk:
        return forbidden(
            "You can only view reviews for products in your own stores."
        )

    queryset = product.reviews_product.select_related(
        "product", "author"
    ).order_by("-created_at", "-id")
    return paginated(request, queryset, ReviewSerializer)
