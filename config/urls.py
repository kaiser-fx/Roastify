"""
URL configuration for Roastify.
"""

from django.urls import include, path

from apps.api.views import healthz

urlpatterns = [
    path("", include("apps.web.urls")),
    path("api/", include("apps.api.urls")),
    path("healthz", healthz, name="healthz"),
]
