"""
URL configuration for nonprofit_app project.
"""
from django.contrib import admin
from django.urls import path, include
from audit import callback_views
import nested_admin

urlpatterns = [
    # Put custom URLs FIRST, before admin
    path("audit/", include("audit.urls")),

    # Then the admin and other URLs
    path("admin/", admin.site.urls),
    path("_nested_admin/", include("nested_admin.urls")),
]