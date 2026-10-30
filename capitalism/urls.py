from django.contrib import admin
from django.urls import include, path

"""
URL routes for the entire capitalism project.
"""

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("shop.urls")),
    path("api/v1/", include("api.urls")),
]
