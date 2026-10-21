"""
API URL configuration.
"""

from django.urls import path
from apps.api import views

app_name = "api"

urlpatterns = [
    path("roast/", views.roast, name="roast"),
]
