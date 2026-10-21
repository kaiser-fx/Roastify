"""
Web app URL configuration.
Registers web:landing, web:results, and web:fallback URL names
as specified in DESIGN.md.
"""

from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("results/", views.results, name="results"),
    path("fallback/", views.fallback, name="fallback"),
]
