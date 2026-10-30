# shop/urls.py
from django.urls import path

from . import views

"""
URL routes for the shop app.
"""

app_name = "shop"

urlpatterns = [
    # HOME
    path("", views.home, name="home"),
    # REDDIT FEED
    path("reddit/", views.reddit_feed, name="reddit_feed"),
    # STORES
    path("my_stores/", views.my_stores, name="my_stores"),
    path("create_store/", views.create_store, name="create_store"),
    path("stores/<int:pk>/edit/", views.edit_store, name="edit_store"),
    path("stores/<int:pk>/delete/", views.delete_store, name="delete_store"),
    # PRODUCTS - VENDORS
    path("products/", views.my_products, name="my_products"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/<int:pk>/edit/", views.edit_product, name="edit_product"),
    path(
        "products/<int:pk>/delete/",
        views.delete_product,
        name="delete_product",
    ),
    # PRODUCTS - BUYERS
    path("products/browse/", views.product_list, name="product_list"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    # REVIEWS -  PRODUCT/BUYER
    path("product/<int:pk>/review/", views.add_review, name="add_review"),
    # CART - BUYERS
    path(
        "cart/add/<int:pk>/", views.add_item_to_cart, name="add_item_to_cart"
    ),
    path("cart/", views.cart_page, name="cart_page"),
    path(
        "cart/remove/<int:pk>/",
        views.remove_cart_item,
        name="remove_cart_item",
    ),
    path("checkout/", views.checkout, name="checkout"),
    path(
        "invoice/<int:pk>/",
        views.invoice_confirmation,
        name="invoice_confirmation",
    ),
]
