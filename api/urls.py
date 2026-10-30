"""URL routes for the REST API (mounted at /api/v1/)."""

from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    # Entry points
    path("", views.api_root, name="root"),
    path("vendors/", views.vendor_list, name="vendors"),
    path("stores/", views.stores, name="stores"),
    path("products/", views.products, name="products"),
    path("reviews/", views.reviews, name="reviews"),
    # Nested resources
    path(
        "vendors/<int:vendor_id>/stores/",
        views.vendor_stores,
        name="vendor_stores",
    ),
    path(
        "stores/<int:store_id>/products/",
        views.store_products,
        name="store_products",
    ),
    path(
        "products/<int:product_id>/reviews/",
        views.product_reviews,
        name="product_reviews",
    ),
]
