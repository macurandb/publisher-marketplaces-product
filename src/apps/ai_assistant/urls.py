"""
URLs for AI assistant
"""

from django.urls import path

from .views import EnhanceProductView

urlpatterns = [
    path("enhance-product/", EnhanceProductView.as_view(), name="enhance-product"),
]
